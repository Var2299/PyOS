from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.utils import log_action, notify_owner

from .models import Node
from .serializers import NodeSerializer


class NodeViewSet(viewsets.ModelViewSet):
    
    serializer_class = NodeSerializer
    permission_classes = [IsAuthenticated]

    # ----- helpers ---------------------------------------------------------

    @property
    def is_admin(self):
        u = self.request.user
        return bool(u and (u.is_admin_role or u.is_staff))

    def get_queryset(self):
        """Base queryset = everything this user is allowed to SEE."""
        user = self.request.user
        if self.is_admin:
            return Node.objects.all()
        return Node.objects.filter(
            Q(owner=user)
            | Q(permission_level__in=[Node.READ_ONLY, Node.PUBLIC])
        )

    def get_owned_queryset(self):
        """Nodes actually owned by the user (for recycle bin / stats)."""
        return Node.objects.filter(owner=self.request.user)

    def get_active_queryset(self):
        return self.get_queryset().filter(is_deleted=False)

    def _can_edit(self, node):
        user = self.request.user
        if node.owner_id == user.id or self.is_admin:
            return True
        return node.permission_level == Node.PUBLIC

    def _can_delete_or_reconfigure(self, node):
        """Deleting or changing permissions is owner/admin only, even for public."""
        user = self.request.user
        return node.owner_id == user.id or self.is_admin

    # ----- list ------------------------------------------------------------

    def list(self, request, *args, **kwargs):
        """List children of a directory. ?parent=<id> or root if omitted."""
        parent_id = request.query_params.get("parent")
        user = request.user
        if parent_id in (None, "", "null", "root"):
            # At the root level, always show the user's OWN top-level nodes plus
            # other users' explicitly shared (read-only/public) top-level nodes.
            # We intentionally do NOT dump every user's root here for admins —
            # otherwise an admin sees everyone's home/tmp merged together. Admins
            # keep their sudo power to open/edit/delete any node they navigate
            # into (handled in get_object / the action methods below).
            qs = Node.objects.filter(is_deleted=False, parent__isnull=True).filter(
                Q(owner=user)
                | Q(permission_level__in=[Node.READ_ONLY, Node.PUBLIC])
            )
        else:
            # Inside a directory, use the normal visibility rules (which include
            # the admin sudo override), so admins can drill into any subtree.
            qs = self.get_active_queryset().filter(parent_id=parent_id)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    # ----- create / update / delete with permission enforcement ------------

    def perform_create(self, serializer):
        # Admins can create nodes inside another user's workspace (the "All
        # Workspaces" screen). In that case the new node is owned by that
        # workspace's user, not the admin — the admin is acting *inside* their
        # space, like root creating a file in /home/alice. A regular user can
        # only ever create nodes owned by themselves.
        owner = self.request.user
        owner_id = self.request.data.get("owner_id")
        if owner_id and self.is_admin:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            target = User.objects.filter(id=owner_id).first()
            if target:
                owner = target
        node = serializer.save(owner=owner)
        actor = self.request.user
        suffix = "" if node.owner_id == actor.id else f" (in {node.owner.username}'s workspace)"
        log_action(actor, "CREATE", f"Created {node.node_type} '{node.path}'{suffix}")
        notify_owner(actor, node, "created")

    def update(self, request, *args, **kwargs):
        node = self.get_object()
        if not self._can_edit(node):
            raise PermissionDenied("You don't have permission to edit this item.")
        # Only owner/admin may change the permission level.
        if "permission_level" in request.data and not self._can_delete_or_reconfigure(node):
            raise PermissionDenied("Only the owner can change sharing settings.")
        # Remember whether this was a sharing change, for the owner notice.
        self._was_share_change = "permission_level" in request.data
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        node = serializer.save()
        actor = self.request.user
        suffix = "" if node.owner_id == actor.id else f" (owner: {node.owner.username})"
        log_action(actor, "UPDATE", f"Updated {node.node_type} '{node.path}'{suffix}")
        verb = "changed sharing of" if getattr(self, "_was_share_change", False) else "updated"
        notify_owner(actor, node, verb)

    def destroy(self, request, *args, **kwargs):
        """Soft-delete: move node (and its subtree) to the recycle bin."""
        node = self.get_object()
        if node.is_protected:
            raise PermissionDenied(
                f"'{node.name}' is a protected system directory and cannot be deleted."
            )
        if not self._can_delete_or_reconfigure(node):
            raise PermissionDenied("You don't have permission to delete this item.")
        self._soft_delete_recursive(node)
        actor = request.user
        suffix = "" if node.owner_id == actor.id else f" (owner: {node.owner.username})"
        log_action(actor, "DELETE", f"Moved '{node.path}' to recycle bin{suffix}")
        notify_owner(actor, node, "deleted")
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _soft_delete_recursive(self, node):
        now = timezone.now()
        node.is_deleted = True
        node.deleted_at = now
        node.save(update_fields=["is_deleted", "deleted_at"])
        for child in node.children.filter(is_deleted=False):
            self._soft_delete_recursive(child)

    # ----- recycle bin -----------------------------------------------------

    @action(detail=False, methods=["get"])
    def recycle_bin(self, request):
        """List top-level deleted nodes the user owns (admins: all deleted)."""
        base = Node.objects.all() if self.is_admin else self.get_owned_queryset()
        deleted = base.filter(is_deleted=True)
        top_level = [n for n in deleted if n.parent is None or not n.parent.is_deleted]
        serializer = self.get_serializer(top_level, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        """Restore a node and its subtree from the recycle bin."""
        node = self.get_object()
        if not self._can_delete_or_reconfigure(node):
            raise PermissionDenied("You don't have permission to restore this item.")
        self._restore_recursive(node)
        log_action(request.user, "RESTORE", f"Restored '{node.path}' from recycle bin")
        notify_owner(request.user, node, "restored")
        return Response(self.get_serializer(node).data)

    def _restore_recursive(self, node):
        node.is_deleted = False
        node.deleted_at = None
        node.save(update_fields=["is_deleted", "deleted_at"])
        for child in node.children.filter(is_deleted=True):
            self._restore_recursive(child)

    @action(detail=True, methods=["delete"])
    def purge(self, request, pk=None):
        """Permanently delete a node from the recycle bin."""
        node = self.get_object()
        if not self._can_delete_or_reconfigure(node):
            raise PermissionDenied("You don't have permission to purge this item.")
        path = node.path
        notify_owner(request.user, node, "permanently deleted")
        node.delete()
        log_action(request.user, "PURGE", f"Permanently deleted '{path}'")
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"])
    def shared_with_me(self, request):
        """List items other users have shared (read-only/public) with everyone.

        Only the *topmost* shared item in any chain is returned: if alice shares
        a folder 'projects' and also a file inside it, you see 'projects' (you
        can navigate in to find the rest). This keeps the list tidy and mirrors
        how you'd present "things shared with me" in a real system.
        """
        user = request.user
        shared = Node.objects.filter(
            is_deleted=False,
            permission_level__in=[Node.READ_ONLY, Node.PUBLIC],
        ).exclude(owner=user).select_related("parent", "owner")

        top_level = []
        for node in shared:
            parent = node.parent
            # Include it only if its parent is NOT itself a shared node owned by
            # the same person (otherwise it's reachable by navigating in).
            if (
                parent is None
                or parent.owner_id != node.owner_id
                or parent.permission_level == Node.PRIVATE
            ):
                top_level.append(node)
        return Response(self.get_serializer(top_level, many=True).data)

    # ----- admin: All Workspaces ------------------------------------------

    @action(detail=False, methods=["get"])
    def workspaces(self, request):
       
        if not self.is_admin:
            raise PermissionDenied("Admin access required.")
        from django.contrib.auth import get_user_model
        User = get_user_model()
        result = []
        for u in User.objects.all().order_by("username"):
            active = Node.objects.filter(owner=u, is_deleted=False)
            result.append({
                "id": u.id,
                "username": u.username,
                "is_admin": bool(u.is_admin_role or u.is_staff),
                "files": active.filter(node_type=Node.FILE).count(),
                "directories": active.filter(node_type=Node.DIRECTORY).count(),
            })
        return Response(result)

    @action(detail=False, methods=["get"])
    def workspace(self, request):
        """Admin only: browse a specific user's filesystem.

        ?user=<id> (required) selects whose workspace to view.
        ?parent=<id> selects a folder within it; omitted means that user's root.
        Returns ALL nodes including private ones (full sudo), so the admin can
        manage anything in that user's space.
        """
        if not self.is_admin:
            raise PermissionDenied("Admin access required.")
        user_id = request.query_params.get("user")
        if not user_id:
            return Response({"detail": "user is required"}, status=status.HTTP_400_BAD_REQUEST)

        parent_id = request.query_params.get("parent")
        qs = Node.objects.filter(owner_id=user_id, is_deleted=False)
        if parent_id in (None, "", "null", "root"):
            qs = qs.filter(parent__isnull=True)
        else:
            qs = qs.filter(parent_id=parent_id)
        return Response(self.get_serializer(qs.order_by("node_type", "name"), many=True).data)

    # ----- stats & search --------------------------------------------------

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Workspace summary counts for the dashboard (the user's own nodes)."""
        owned = self.get_owned_queryset()
        active = owned.filter(is_deleted=False)
        return Response({
            "files": active.filter(node_type=Node.FILE).count(),
            "directories": active.filter(node_type=Node.DIRECTORY).count(),
            "deleted": owned.filter(is_deleted=True).count(),
        })

    @action(detail=False, methods=["get"])
    def search(self, request):
        """Search visible nodes by name or content. ?q=<term>"""
        term = request.query_params.get("q", "").strip()
        if not term:
            return Response([])
        qs = self.get_active_queryset().filter(
            Q(name__icontains=term) | Q(content__icontains=term)
        )
        log_action(request.user, "SEARCH", f"Searched for '{term}'")
        return Response(self.get_serializer(qs, many=True).data)

from .models import ActivityLog


def log_action(user, action, detail=""):
    """Central helper to record an audit log entry for the actor."""
    ActivityLog.objects.create(user=user, action=action, detail=detail)


def _actor_label(actor):
    """Human-readable 'name (role)' for a log message, e.g. 'root (admin)'."""
    role = "admin" if (actor.is_admin_role or actor.is_staff) else "user"
    return f"{actor.username} ({role})"


def notify_owner(actor, node, verb, action="OWNER_NOTICE"):
    
    
    if node.owner_id == actor.id:
        return  # acting on your own item — no cross-user notice needed

    # The folder the item lives in (its parent path), shown to the owner for context.
    location = node.parent.path if node.parent else "/"
    detail = f"{_actor_label(actor)} {verb} '{node.name}' in your {location}"
    ActivityLog.objects.create(user=node.owner, action=action, detail=detail)

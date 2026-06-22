import shlex

from .models import Node


class CommandResult:
    """Bundles command output plus the (possibly changed) working directory."""

    def __init__(self, output, cwd):
        self.output = output
        self.cwd = cwd


class CommandEngine:
    def __init__(self, user, cwd=None):
        self.user = user
        self.is_admin = bool(user.is_admin_role or user.is_staff)
        # cwd is a list of path segments, e.g. ["home", "alice"].
        self.cwd = list(cwd or [])

    # ---------- public entry point ----------

    def execute(self, raw):
        """Parse and run a single command line, returning a CommandResult."""
        raw = (raw or "").strip()
        if not raw:
            return CommandResult("", self.cwd)
        try:
            tokens = shlex.split(raw)
        except ValueError:
            return CommandResult("error: could not parse command", self.cwd)
        if not tokens:
            return CommandResult("", self.cwd)

        name, args = tokens[0], tokens[1:]
        handler = getattr(self, f"cmd_{name}", None)
        if handler is None:
            return CommandResult(f"pyos: command not found: '{name}' (try 'help')", self.cwd)
        output = handler(args)
        return CommandResult(output, self.cwd)

    # ---------- path + permission helpers ----------

    def _user_nodes(self):
        """Active nodes owned by this user (their personal filesystem tree)."""
        return Node.objects.filter(owner=self.user, is_deleted=False)

    def _resolve(self, path_string):
        """Resolve a path string into a list of segments, handling . and .."""
        if path_string.startswith("/"):
            segments = []
        else:
            segments = self.cwd[:]
        for part in path_string.split("/"):
            if not part or part == ".":
                continue
            if part == "..":
                if segments:
                    segments.pop()
            else:
                segments.append(part)
        return segments

    def _find(self, segments):
        """Walk the user's tree by segment names; return the Node or None.

        The root (empty segment list) is represented by None, meaning the
        top level where the user's parent-less nodes live.
        """
        parent = None
        for seg in segments:
            qs = self._user_nodes().filter(parent=parent, name=seg)
            node = qs.first()
            if node is None:
                return "MISSING"
            parent = node
        return parent  # None means we're at root

    def _children_of(self, node):
        return self._user_nodes().filter(parent=node)

    def _can(self, node, access):
        """Permission check mirroring the CLI's _has_permission.

        access is one of 'r', 'w', 'x'. Root (None) is always traversable.
        """
        if node is None:  # the synthetic root: readable/traversable, not writable by guests
            return True
        if self.is_admin or node.owner_id == self.user.id:
            return True
        # Non-owners: writes never allowed; reads/traverse allowed for shared nodes.
        if access == "w":
            return False
        return node.permission_level in (Node.READ_ONLY, Node.PUBLIC)

    def _cwd_string(self):
        return "/" + "/".join(self.cwd)

    # ---------- commands ----------

    def cmd_help(self, args):
        return (
            "Supported commands:\n"
            "  pwd                 print working directory\n"
            "  ls [path]           list directory contents\n"
            "  tree                show your whole directory tree\n"
            "  cd <path>           change directory\n"
            "  mkdir <name>        create a directory\n"
            "  touch <name>        create an empty file\n"
            "  cat <file>          print file contents\n"
            "  echo \"text\" > file  write text to a file (>> to append)\n"
            "  rm [-r] <path>      remove a file or directory\n"
            "  chmod <perm> <path> set sharing: private | read_only | public\n"
            "  whoami              show current user and role\n"
            "  history             show recent commands\n"
            "  clear               clear the screen"
        )

    def cmd_pwd(self, args):
        return self._cwd_string()

    def cmd_whoami(self, args):
        role = "admin" if self.is_admin else "user"
        return f"{self.user.username} ({role})"

    def cmd_history(self, args):
        # Mirrors the CLI's run_history: numbered list of the user's past
        # commands. Reads from the CommandHistory table (oldest first).
        from apps.core.models import CommandHistory

        commands = list(
            CommandHistory.objects.filter(user=self.user)
            .order_by("created_at")
            .values_list("command", flat=True)
        )
        if not commands:
            return "(no command history yet)"
        return "\n".join(f"{i:>3}  {cmd}" for i, cmd in enumerate(commands, 1))

    def cmd_tree(self, args):
        """Show the logged-in user's entire directory tree (their own nodes only).

        Builds the hierarchy in memory from a single query, then renders it with
        box-drawing connectors like the real `tree` command. Only the current
        user's own nodes are included — never another user's tree.
        """
        nodes = list(
            Node.objects.filter(owner=self.user, is_deleted=False).order_by(
                "node_type", "name"
            )
        )
        # Group children by parent id (None = root level).
        children_by_parent = {}
        for n in nodes:
            children_by_parent.setdefault(n.parent_id, []).append(n)

        lines = ["."]
        dirs = files = 0

        def walk(parent_id, prefix):
            nonlocal dirs, files
            kids = children_by_parent.get(parent_id, [])
            for i, node in enumerate(kids):
                last = i == len(kids) - 1
                connector = "└── " if last else "├── "
                suffix = "/" if node.is_directory else ""
                lines.append(f"{prefix}{connector}{node.name}{suffix}")
                if node.is_directory:
                    dirs += 1
                    extension = "    " if last else "│   "
                    walk(node.id, prefix + extension)
                else:
                    files += 1

        walk(None, "")
        if len(lines) == 1:
            return "."  # empty tree
        lines.append("")
        lines.append(f"{dirs} directories, {files} files")
        return "\n".join(lines)

    def cmd_ls(self, args):
        target_segments = self._resolve(args[0]) if args else self.cwd
        node = self._find(target_segments)
        if node == "MISSING":
            return "ls: directory not found"
        if node is not None and not node.is_directory:
            return "ls: not a directory"
        if not self._can(node, "r"):
            return "ls: permission denied"
        children = self._children_of(node).order_by("node_type", "name")
        if not children:
            return "(empty directory)"
        lines = []
        for c in children:
            suffix = "/" if c.is_directory else ""
            perm = {"private": "rwx", "read_only": "r-x", "public": "rwx"}[c.permission_level]
            lines.append(f"{perm}  {c.owner.username:<10}  {c.name}{suffix}")
        return "\n".join(lines)

    def cmd_cd(self, args):
        target = self._resolve(args[0]) if args else ["home", self.user.username]
        node = self._find(target)
        if node == "MISSING":
            return "cd: directory not found"
        if node is not None and not node.is_directory:
            return "cd: not a directory"
        if not self._can(node, "x"):
            return "cd: permission denied"
        self.cwd = target
        return ""  # silent, like a real shell

    def cmd_mkdir(self, args):
        if not args:
            return "usage: mkdir <directory_name>"
        segments = self._resolve(args[0])
        if not segments:
            return "mkdir: invalid path"
        parent = self._find(segments[:-1])
        name = segments[-1]
        if parent == "MISSING":
            return "mkdir: invalid path"
        if parent is not None and not parent.is_directory:
            return "mkdir: invalid path"
        if not self._can(parent, "w"):
            return "mkdir: permission denied"
        if self._children_of(parent).filter(name=name).exists():
            return "mkdir: item already exists"
        Node.objects.create(
            owner=self.user, name=name, node_type=Node.DIRECTORY, parent=parent
        )
        return ""

    def cmd_touch(self, args):
        if not args:
            return "usage: touch <file_name>"
        segments = self._resolve(args[0])
        if not segments:
            return "touch: invalid path"
        parent = self._find(segments[:-1])
        name = segments[-1]
        if parent == "MISSING" or (parent is not None and not parent.is_directory):
            return "touch: invalid path"
        if not self._can(parent, "w"):
            return "touch: permission denied"
        if self._children_of(parent).filter(name=name).exists():
            return ""  # touch on an existing file is a no-op here
        Node.objects.create(
            owner=self.user, name=name, node_type=Node.FILE, parent=parent
        )
        return ""

    def cmd_cat(self, args):
        if not args:
            return "usage: cat <file_name>"
        node = self._find(self._resolve(args[0]))
        if node == "MISSING" or node is None or node.is_directory:
            return "cat: file not found"
        if not self._can(node, "r"):
            return "cat: permission denied"
        return node.content if node.content else "(file empty)"

    def cmd_echo(self, args):
        # Supports: echo "text" > file   and   echo "text" >> file
        if len(args) >= 2 and args[-2] in (">", ">>"):
            text = " ".join(args[:-2])
            mode = args[-2]
            target = args[-1]
            segments = self._resolve(target)
            if not segments:
                return "echo: invalid destination"
            parent = self._find(segments[:-1])
            name = segments[-1]
            if parent == "MISSING" or (parent is not None and not parent.is_directory):
                return "echo: invalid destination"
            if not self._can(parent, "w"):
                return "echo: permission denied"
            node = self._children_of(parent).filter(name=name).first()
            if node is None:
                node = Node.objects.create(
                    owner=self.user, name=name, node_type=Node.FILE, parent=parent
                )
            if node.is_directory or not self._can(node, "w"):
                return "echo: cannot write to target"
            if mode == ">":
                node.content = text
            else:
                node.content = (node.content + "\n" + text) if node.content else text
            node.save(update_fields=["content"])
            return ""
        # plain echo just prints
        return " ".join(args)

    def cmd_rm(self, args):
        if not args:
            return "usage: rm [-r] <path>"
        recursive = "-r" in args
        target_name = next((a for a in args if a != "-r"), None)
        if not target_name:
            return "usage: rm [-r] <path>"
        segments = self._resolve(target_name)
        node = self._find(segments)
        if node == "MISSING" or node is None:
            return "rm: item not found"
        is_owner = node.owner_id == self.user.id
        if not (self.is_admin or is_owner):
            return "rm: permission denied (you do not own this item)"
        if node.is_protected:
            return f"rm: cannot remove '{node.name}': it is a protected system directory"
        if node.is_directory and self._children_of(node).exists() and not recursive:
            return "rm: directory is not empty (use -r)"
        # Soft-delete to the recycle bin, recursively (consistent with the web app).
        self._soft_delete(node)
        return ""

    def _soft_delete(self, node):
        from django.utils import timezone
        node.is_deleted = True
        node.deleted_at = timezone.now()
        node.save(update_fields=["is_deleted", "deleted_at"])
        for child in Node.objects.filter(parent=node, is_deleted=False):
            self._soft_delete(child)

    def cmd_chmod(self, args):
        if len(args) < 2:
            return "usage: chmod <private|read_only|public> <path>"
        level, target = args[0], args[1]
        valid = {Node.PRIVATE, Node.READ_ONLY, Node.PUBLIC}
        if level not in valid:
            return "chmod: permission must be one of private, read_only, public"
        node = self._find(self._resolve(target))
        if node == "MISSING" or node is None:
            return "chmod: target not found"
        if not (self.is_admin or node.owner_id == self.user.id):
            return "chmod: only owner or admin can change permissions"
        node.permission_level = level
        node.save(update_fields=["permission_level"])
        return ""

    def cmd_clear(self, args):
        # Signal the frontend to clear; handled client-side.
        return "\x0c"

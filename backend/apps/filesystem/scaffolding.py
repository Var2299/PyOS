
from .models import Node


def create_home_for(user):
    """Create /home/<username> for a newly registered user.

    Idempotent: does nothing if the user already has a home directory.
    """
    if Node.objects.filter(owner=user, name="home", parent__isnull=True).exists():
        return

    home = Node.objects.create(
        owner=user, name="home", node_type=Node.DIRECTORY, parent=None
    )
    user_home = Node.objects.create(
        owner=user, name=user.username, node_type=Node.DIRECTORY, parent=home
    )
    # A friendly starter file in the user's home, like a real account skeleton.
    Node.objects.create(
        owner=user,
        name="welcome.txt",
        node_type=Node.FILE,
        parent=user_home,
        content=(
            f"Welcome to PyOS, {user.username}!\n\n"
            "This is your home directory. Try these in the Terminal:\n"
            "  pwd            see where you are\n"
            "  ls             list files here\n"
            "  tree           view your whole directory tree\n"
            "  mkdir projects make a folder\n"
            "  touch notes.md make a file\n"
            "  help           see all commands\n"
        ),
    )

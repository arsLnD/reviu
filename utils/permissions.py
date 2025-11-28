from config import config


def is_admin(user_id: int) -> bool:
    """
    Check whether a user is an admin based on the ADMIN_IDS env variable.
    Owner is treated as admin automatically.
    """
    return user_id == config.bot.owner_id or user_id in config.bot.admin_ids



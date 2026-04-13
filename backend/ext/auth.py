"""ext-internal Auth-Helpers.

Wrapper-Funktionen die wir im ext/-Code statt der Onyx-FOSS-Originale nutzen,
um Upstream-Sync-Brueche zu vermeiden. Onyx hat in PR #9930 die Funktion
``current_admin_user`` aus ``onyx.auth.users`` entfernt (Migration zu
account-type-basiertem Permission-System). Da unsere ext-Router weiterhin
den klassischen "Nur Admin"-Check brauchen, definieren wir ihn hier neu.

Bei zukuenftigen Sync-Aenderungen am Auth-System ist ext/auth.py die einzige
Stelle, an der wir nachziehen muessen — alle ext-Router importieren von hier.
"""

from fastapi import Depends

from onyx.auth.users import current_user
from onyx.db.models import User
from onyx.db.models import UserRole
from onyx.server.utils import BasicAuthenticationError


async def current_admin_user(user: User = Depends(current_user)) -> User:
    """Stellt sicher, dass der eingeloggte User die Rolle ADMIN hat.

    Replikat der bis zu Onyx PR #9930 in onyx.auth.users definierten
    Funktion. Wirft ``BasicAuthenticationError`` wenn der User nicht Admin ist.
    """
    if user.role != UserRole.ADMIN:
        raise BasicAuthenticationError(
            detail="Access denied. User must be an admin to perform this action.",
        )
    return user

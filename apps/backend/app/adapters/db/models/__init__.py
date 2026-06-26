# Modelos ORM — SQLAlchemy
from app.adapters.db.models.accounting import Base  # noqa: F401

# Registrar modelos de autenticación en metadata
import app.models.user  # noqa: F401

from app.adapters.db.models.accounting import (  # noqa: F401
    Account,
    Base,
    CashflowProjection,
    Company,
    JournalEntry,
    JournalEntryLine,
    KardexMovement,
    Product,
    ProductCategory,
    ProductUnit,
)
from app.adapters.db.models.sales import (  # noqa: F401
    PosSession,
    Sale,
    SaleItem,
    SalePayment,
    RestaurantSale,
    HardwareSale,
)
from app.adapters.db.models.restaurant import (  # noqa: F401
    RestaurantSection,
    Table,
    MenuItem,
    MenuModifier,
    Recipe,
    RecipeIngredient,
    KitchenOrder,
    TakeawayOrder,
    Promotion,
    InvestmentItem,
)
from app.adapters.db.models.simulator import Scenario  # noqa: F401

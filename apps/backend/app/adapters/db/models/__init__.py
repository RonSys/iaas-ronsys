# Modelos ORM — SQLAlchemy
# Registrar modelos de autenticación en metadata
import app.models.user  # noqa: F401
from app.adapters.db.models.accounting import (  # noqa: F401
    Account,
    Base,  # noqa: F401
    CashflowProjection,
    Company,
    JournalEntry,
    JournalEntryLine,
    KardexMovement,
    Product,
    ProductCategory,
    ProductUnit,
)
from app.adapters.db.models.calls import (  # noqa: F401
    ACTIVE_STATUSES,
    AI_STATES,
    CALL_DIRECTIONS,
    CALL_STATUSES,
    TRANSFER_REASONS,
    CallRecord,
    CallTranscription,
    TERMINAL_STATUSES,
)
from app.adapters.db.models.delivery import (  # noqa: F401
    Courier,
    DeliveryOrder,
    DeliveryZone,
    MarketingCampaign,
)
from app.adapters.db.models.restaurant import (  # noqa: F401
    InvestmentItem,
    KitchenOrder,
    MenuItem,
    MenuModifier,
    Promotion,
    Recipe,
    RecipeIngredient,
    RestaurantSection,
    Table,
    TakeawayOrder,
)
from app.adapters.db.models.sales import (  # noqa: F401
    HardwareSale,
    PosSession,
    RestaurantSale,
    Sale,
    SaleItem,
    SalePayment,
)
from app.adapters.db.models.assistant import (  # noqa: F401
    QueryCatalog,
    QueryLog,
)
from app.adapters.db.models.simulator import Scenario  # noqa: F401

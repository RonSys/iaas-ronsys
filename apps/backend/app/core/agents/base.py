"""
🤖 Puerto Abstracto — Sistema de Skills IA

⏰ DEUDA TÉCNICA (#8)
   Diseñado como puerto hexagonal ANTES de implementar skills concretos.
   Esto permite extraerlo a servicio independiente sin cambiar el dominio.

   Ver: proyecto-franquicia/gestion/recordatorios.md

   🏗️ TO-DO:
     - Implementar skills concretos (VentasSkill, InventarioSkill, FinanzasSkill)
     - SkillLoader que descubre skills por decorador/registro
     - AgenteOrquestador que coordina skills vía LLM
     - Tests unitarios para cada skill
     - Conectar con LLM provider real (OpenAI/DeepSeek)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


# ═══════════════════════════════════════════════════════════════
# Entidades del Dominio
# ═══════════════════════════════════════════════════════════════


@dataclass
class SkillResult:
    """Resultado de la ejecución de una skill."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentContext:
    """Contexto de ejecución para un agente/skill."""
    company_id: int
    user_id: Optional[int] = None
    language: str = "es"
    extra: dict[str, Any] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════
# Puerto Abstracto (Hexagonal)
# ═══════════════════════════════════════════════════════════════


class BaseSkill(ABC):
    """
    Puerto abstracto para skills de IA.

    Cada skill es una capacidad concreta del sistema (ventas, inventario,
    finanzas) que puede ser invocada por un agente orquestador vía LLM.

    🏗️ IMPLEMENTACIONES CONCRETAS (deuda técnica):
      - SalesSkill:     analiza ventas, predicciones, alertas
      - InventorySkill: stock bajo, rotación, sugerencias de compra
      - FinanceSkill:   proyecciones, alertas de flujo de caja
      - ReportSkill:    generación de reportes financieros

    Principio: las skills son STATELESS y reciben todo su contexto
    como parámetro. Esto permite escalar horizontalmente.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre único de la skill (ej: 'sales', 'inventory', 'finance')."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Descripción para que el LLM sepa cuándo invocarla."""
        ...

    @abstractmethod
    async def execute(self, context: AgentContext, params: dict[str, Any]) -> SkillResult:
        """
        Ejecuta la skill con el contexto y parámetros dados.

        Args:
            context: AgentContext con company_id, user_id, etc.
            params: Parámetros específicos de la skill (ej: fechas, filtros)

        Returns:
            SkillResult con success, data y error opcional.
        """
        ...


# ═══════════════════════════════════════════════════════════════
# Registry de Skills
# ═══════════════════════════════════════════════════════════════


class SkillRegistry:
    """
    Registro central de skills disponibles.

    🏗️ TO-DO:
      - Descubrimiento automático de skills (decorator o entry_points)
      - Validación de unicidad de nombres
      - Hot-reload de skills en desarrollo
    """

    def __init__(self):
        self._skills: dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill) -> None:
        """Registra una skill."""
        if skill.name in self._skills:
            raise ValueError(f"Skill '{skill.name}' ya registrada")
        self._skills[skill.name] = skill

    def get(self, name: str) -> Optional[BaseSkill]:
        """Obtiene una skill por nombre."""
        return self._skills.get(name)

    def list_skills(self) -> list[dict[str, str]]:
        """Lista todas las skills con nombre y descripción."""
        return [
            {"name": s.name, "description": s.description}
            for s in self._skills.values()
        ]

    def get_skills_context(self) -> str:
        """
        Genera contexto para el LLM con todas las skills disponibles.
        El LLM usa esto para decidir qué skill invocar.
        """
        lines = []
        for s in self._skills.values():
            lines.append(f"- {s.name}: {s.description}")
        return "\n".join(lines)


# Singleton
skill_registry = SkillRegistry()

"""
🤖 Sistema de Agentes de IA — Skills.

⏰ DEUDA TÉCNICA (#8)
   Ver: proyecto-franquicia/gestion/recordatorios.md
   Principio: Diseñar interfaces hexagonales antes de implementar.

   Este módulo requiere:
     1. Diseñar puerto abstracto BaseSkill (ABC) → hecho abajo ↓
     2. Implementar SkillLoader dinámico
     3. Skills concretos: ventas, inventario, finanzas
     4. Conectar con LLM provider (OpenAI/DeepSeek via API key en .env)
     5. Rate limiting por tenant/endpoint

   🏗️ CUANDO SE IMPLEMENTE:
     - Extraer a servicio independiente si el consumo de CPU es alto
     - Usar cola de mensajes (RabbitMQ) para tareas pesadas
     - Las skills deben ser stateless y testables en aislamiento
"""

from app.core.agents.base import (  # noqa: F401
    AgentContext,
    BaseSkill,
    SkillRegistry,
    SkillResult,
)

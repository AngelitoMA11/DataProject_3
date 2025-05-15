
from typing import Dict, List, Optional, Union


class BudgetControl:
    def __init__(self):
        self.total_budget: float = 0.0
        self.remaining_budget: float = 0.0
        self.expenses: Dict[str, float] = {}
        self.details: Dict[str, Union[Dict, List[Dict]]] = {}

    def initialize_budget(self, total_budget: float):
        """Inicializa el presupuesto del viaje."""
        if total_budget <= 0:
            raise ValueError("El presupuesto debe ser mayor que cero.")
        self.total_budget = total_budget
        self.remaining_budget = total_budget
        self.expenses = {}
        self.details = {}
        print(f"[BudgetControl] Presupuesto inicializado: {total_budget} €")

    def register_expense(self, category: str, amount: float, metadata: Optional[Dict] = None):
        """Registra un gasto en una categoría específica."""
        if amount <= 0:
            raise ValueError("El monto del gasto debe ser positivo.")
        if amount > self.remaining_budget:
            raise ValueError("El gasto excede el presupuesto restante.")

        self.expenses[category] = self.expenses.get(category, 0.0) + amount
        self.remaining_budget -= amount

        if metadata:
            if category not in self.details:
                self.details[category] = []
            elif not isinstance(self.details[category], list):
                self.details[category] = [self.details[category]]
            self.details[category].append(metadata)

        print(f"[BudgetControl] Gasto registrado: {amount} € en '{category}'. Presupuesto restante: {self.remaining_budget} €")

    def get_remaining_budget(self) -> float:
        """Devuelve el presupuesto disponible."""
        return self.remaining_budget

    def get_budget_report(self) -> Dict:
        """Devuelve un resumen detallado del presupuesto y los gastos."""
        return {
            "total_budget": round(self.total_budget, 2),
            "expenses": {k: round(v, 2) for k, v in self.expenses.items()},
            "remaining_budget": round(self.remaining_budget, 2),
            "details": self.details
        }

    def print_report(self):
        """Imprime el resumen del presupuesto de forma legible."""
        report = self.get_budget_report()
        print("\n📊 [BudgetControl] Resumen de Presupuesto")
        print(f"Presupuesto total: {report['total_budget']} €")
        print("Gastos:")
        for category, amount in report["expenses"].items():
            print(f"  - {category}: {amount} €")
        print(f"Presupuesto restante: {report['remaining_budget']} €")

        print("\nDetalles:")
        for category, items in report["details"].items():
            print(f"  [{category.upper()}]")
            if isinstance(items, list):
                for item in items:
                    print("   • " + ", ".join(f"{k}: {v}" for k, v in item.items()))
            else:
                print("   • " + ", ".join(f"{k}: {v}" for k, v in items.items()))


                

# Importar la tool

# Inicializar instancia
budget = BudgetControl()

# Inicializar presupuesto total
budget.initialize_budget(2000)

# Registrar gasto del vuelo
budget.register_expense("flight", 600, metadata={"airline": "Iberia", "date": "2025-07-10"})

# Registrar gasto del alojamiento
budget.register_expense("accommodation", 800, metadata={"hotel": "Tokyo Inn", "nights": 5})

# Consultar presupuesto restante
remaining = budget.get_remaining_budget()
print(f"Presupuesto disponible para itinerario: {remaining} €")

# Registrar gasto del itinerario
budget.register_expense("itinerary", 500, metadata={"activity": "Tour Monte Fuji", "price": 500})

# Imprimir resumen final
budget.print_report()
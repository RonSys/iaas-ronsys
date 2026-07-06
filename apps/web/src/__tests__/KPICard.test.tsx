import { render, screen } from "@testing-library/react";
import { KPICard, TrafficLight, fmtCurrency, fmtPct, fmtNum } from "@/components/dashboard/KPICard";

describe("KPICard", () => {
  it("renders title and value", () => {
    render(<KPICard title="Ventas" value="S/ 25,000" />);
    expect(screen.getByText("Ventas")).toBeInTheDocument();
    expect(screen.getByText("S/ 25,000")).toBeInTheDocument();
  });

  it("renders subtitle when provided", () => {
    render(<KPICard title="Margen" value="60%" subtitle="Meta: >50%" />);
    expect(screen.getByText("Meta: >50%")).toBeInTheDocument();
  });

  it("renders trend indicator", () => {
    render(<KPICard title="Ventas" value="S/ 30,000" trend="up" trendLabel="+5%" />);
    expect(screen.getByText("↑ +5%")).toBeInTheDocument();
  });

  it("renders icon when provided", () => {
    render(<KPICard title="Ventas" value="S/ 25,000" icon="💰" />);
    expect(screen.getByText("💰")).toBeInTheDocument();
  });
});

describe("TrafficLight", () => {
  it("renders green status", () => {
    const { container } = render(<TrafficLight status="green" />);
    expect(container.querySelector(".traffic-dot-green")).toBeInTheDocument();
  });

  it("renders yellow status", () => {
    const { container } = render(<TrafficLight status="yellow" />);
    expect(container.querySelector(".traffic-dot-yellow")).toBeInTheDocument();
  });

  it("renders red status", () => {
    const { container } = render(<TrafficLight status="red" />);
    expect(container.querySelector(".traffic-dot-red")).toBeInTheDocument();
  });
});

describe("formatters", () => {
  it("fmtCurrency formats PEN", () => {
    expect(fmtCurrency(25000)).toContain("25,000");
  });

  it("fmtPct formats percentage", () => {
    expect(fmtPct(0.60)).toBe("60.0%");
  });

  it("fmtNum formats number with locale", () => {
    expect(fmtNum(1234.56)).toContain("1,234.6");
  });
});

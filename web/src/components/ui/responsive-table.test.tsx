import { render } from "@solidjs/testing-library";
import { describe, expect, it } from "vitest";
import { ResponsiveTable, type ResponsiveTableColumn } from "./responsive-table";

interface Row { id: string; name: string; status: string; hidden: string; }

const rows: Row[] = [
  { id: "1", name: "Alpha", status: "running", hidden: "h1" },
  { id: "2", name: "Beta", status: "stopped", hidden: "h2" },
];

const cols: ResponsiveTableColumn<Row>[] = [
  { key: "name",   label: "Name",   span: 6, primary: true, render: (r) => <span>{r.name}</span> },
  { key: "status", label: "Status", span: 3, render: (r) => <span>{r.status}</span> },
  { key: "hidden", label: "Hidden", span: 3, hideOnPhone: true, render: (r) => <span>{r.hidden}</span> },
];

describe("ResponsiveTable", () => {
  it("renders a table header with column labels in the desktop layout", () => {
    const { container } = render(() => (
      <ResponsiveTable data={rows} columns={cols} rowKey={(r) => r.id} />
    ));
    const header = container.querySelector("[data-rt-header]") as HTMLElement;
    expect(header.textContent).toContain("Name");
    expect(header.textContent).toContain("Status");
    expect(header.textContent).toContain("Hidden");
  });

  it("renders one row per data item", () => {
    const { container } = render(() => (
      <ResponsiveTable data={rows} columns={cols} rowKey={(r) => r.id} />
    ));
    const renderedRows = container.querySelectorAll("[data-rt-row]");
    expect(renderedRows.length).toBe(2);
  });

  it("renders both desktop row and phone card markup for each row (CSS picks one)", () => {
    const { container } = render(() => (
      <ResponsiveTable data={rows} columns={cols} rowKey={(r) => r.id} />
    ));
    const desktop = container.querySelectorAll("[data-rt-row-desktop]");
    const phone   = container.querySelectorAll("[data-rt-row-phone]");
    expect(desktop.length).toBe(2);
    expect(phone.length).toBe(2);
  });

  it("omits hideOnPhone columns from the phone card layout", () => {
    const { container } = render(() => (
      <ResponsiveTable data={rows} columns={cols} rowKey={(r) => r.id} />
    ));
    const phoneCard = container.querySelector("[data-rt-row-phone]") as HTMLElement;
    expect(phoneCard.textContent).toContain("Alpha");
    expect(phoneCard.textContent).toContain("running");
    expect(phoneCard.textContent).not.toContain("h1");
  });

  it("renders empty state when data is empty and emptyState is provided", () => {
    const { getByText } = render(() => (
      <ResponsiveTable
        data={[]}
        columns={cols}
        rowKey={(r) => r.id}
        emptyState={<div>No rows!</div>}
      />
    ));
    expect(getByText("No rows!")).toBeTruthy();
  });

  it("emits rowKey() output as data-rt-row-key on each row", () => {
    const { container } = render(() => (
      <ResponsiveTable data={rows} columns={cols} rowKey={(r) => `row-${r.id}`} />
    ));
    const rendered = container.querySelectorAll("[data-rt-row]");
    expect(rendered[0].getAttribute("data-rt-row-key")).toBe("row-1");
    expect(rendered[1].getAttribute("data-rt-row-key")).toBe("row-2");
  });

  it("renders rowExtra below each row when provided", () => {
    const { container } = render(() => (
      <ResponsiveTable
        data={rows}
        columns={cols}
        rowKey={(r) => r.id}
        rowExtra={(r) => <div data-extra>{`extra-${r.id}`}</div>}
      />
    ));
    const extras = container.querySelectorAll("[data-extra]");
    expect(extras.length).toBe(2);
    expect(extras[0].textContent).toBe("extra-1");
    expect(extras[1].textContent).toBe("extra-2");
  });

  it("applies rowClass() output to the row wrapper", () => {
    const { container } = render(() => (
      <ResponsiveTable
        data={rows}
        columns={cols}
        rowKey={(r) => r.id}
        rowClass={(r) => (r.status === "running" ? "border-success" : undefined)}
      />
    ));
    const rendered = container.querySelectorAll("[data-rt-row]");
    expect(rendered[0].className).toContain("border-success");
    expect(rendered[1].className).not.toContain("border-success");
  });
});

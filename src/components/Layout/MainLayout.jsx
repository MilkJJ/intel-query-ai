import Sidebar from "./Sidebar";

export default function MainLayout({
  children,
  history,
  activeVideoName,
  onClearHistory,
  onExportPdf,
  onExportPpt,
  canExport,
}) {
  return (
    <div style={{ display: "flex", height: "100vh" }}>
      <Sidebar
        history={history}
        activeVideoName={activeVideoName}
        onClearHistory={onClearHistory}
        onExportPdf={onExportPdf}
        onExportPpt={onExportPpt}
        canExport={canExport}
      />
      <div style={{ flex: 1, background: "#1e1e1e", color: "white" }}>
        {children}
      </div>
    </div>
  );
}
import Sidebar from "./Sidebar";

export default function MainLayout({
  children,
  history,
  activeVideoName,
  onClearHistory,
}) {
  return (
    <div style={{ display: "flex", height: "100vh" }}>
      <Sidebar
        history={history}
        activeVideoName={activeVideoName}
        onClearHistory={onClearHistory}
      />
      <div style={{ flex: 1, background: "#1e1e1e", color: "white" }}>
        {children}
      </div>
    </div>
  );
}
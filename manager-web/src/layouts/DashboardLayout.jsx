import React, { useEffect } from 'react';
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom';
import { LayoutDashboard, Camera, Shield, FileText, Settings, Monitor, Power, Moon, Sun, LogOut } from 'lucide-react';
import useAuthStore from '../store/authStore';
import useDeviceStore from '../store/deviceStore';
import useUIStore from '../store/uiStore';
import MobileBottomNav from '../components/MobileBottomNav';
import { api } from '../lib/api';

export default function DashboardLayout() {
  const { theme, toggleTheme } = useUIStore();
  const { parentEmail, logout, userPermissions } = useAuthStore();
  const { 
    deviceId, 
    deviceName, 
    allDevices, 
    status, 
    serverSource,
    fetchAllDevices,
    fetchStatus,
    fetchServerSource,
    setDevice
  } = useDeviceStore();

  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    fetchAllDevices();
    fetchServerSource();

    // Heartbeat for device status
    const interval = setInterval(() => {
      fetchStatus();
    }, 15000);
    fetchStatus();

    return () => clearInterval(interval);
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const navItems = [
    { id: "overview", label: "Overview", icon: LayoutDashboard, path: "/" },
    { id: "screenshots", label: "Screenshots", icon: Camera, path: "/screenshots", hidden: !userPermissions.can_view_screenshots },
    { id: "rules", label: "Rules & Sync", icon: Shield, path: "/rules", hidden: !userPermissions.can_manage_rules },
    { id: "logs", label: "Live Logs", icon: FileText, path: "/logs", hidden: !userPermissions.can_view_logs },
    { id: "settings", label: "Settings", icon: Settings, path: "/settings" },
  ];

  return (
    <div className="min-h-screen bg-background text-foreground font-sans transition-colors duration-200">
      
      {/* GLOBAL NOTIFICATION BAR FOR SERVER SOURCE */}
      {serverSource === "Vercel-Backup" && (
        <div className="bg-amber-900/40 border-b border-amber-800 text-amber-200 px-4 py-1.5 text-xs font-bold text-center flex items-center justify-center gap-2">
          <Monitor className="w-3.5 h-3.5" />
          <span>Chú ý: Máy chủ chính (T.Lâm) đang ngoại tuyến. Hệ thống đang chạy trên máy chủ phụ (Vercel).</span>
        </div>
      )}

      <div className="max-w-6xl mx-auto min-h-screen relative md:grid md:grid-cols-12 md:gap-6 p-4">
        
        {/* LEFT COLUMN: NAVIGATION */}
        <aside className="hidden md:flex md:col-span-2 flex-col gap-4">
          <div className="p-4 rounded-xl border bg-card border-border shadow-sm flex items-center justify-between">
            <h1 className="text-sm font-extrabold tracking-widest text-primary uppercase leading-tight">
              Parental<br/>Control
            </h1>
          </div>
          
          <nav className="flex-1 space-y-1">
            {navItems.filter(i => !i.hidden).map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path));
              return (
                <NavLink
                  key={item.id}
                  to={item.path}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-bold transition-all
                    ${isActive 
                      ? "bg-primary text-primary-foreground shadow-md" 
                      : "text-foreground hover:bg-secondary"
                    }`}
                >
                  <Icon className="w-4 h-4 stroke-[2]" />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </nav>
        </aside>

        {/* CENTER COLUMN: MAIN CONTENT */}
        <main className="col-span-12 md:col-span-7 space-y-6 pb-20 md:pb-0 h-[calc(100vh-2rem)] overflow-y-auto pr-1 scrollbar-hide">
          
          {/* Mobile Header */}
          <div className="md:hidden flex items-center justify-between p-4 rounded-xl border bg-card border-border mb-4 shadow-sm">
            <h1 className="text-sm font-extrabold tracking-widest text-primary uppercase">
              Parental Control
            </h1>
            <button onClick={toggleTheme} className="p-2 rounded-lg bg-secondary text-foreground hover:opacity-80">
              {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
          </div>

          <Outlet />

        </main>

        {/* RIGHT COLUMN: INFO PANEL & QUICK STATUS */}
        <aside className="hidden md:block md:col-span-3 space-y-6 overflow-y-auto h-full pl-1">
          
          {/* THEME TOGGLE */}
          <button
            onClick={toggleTheme}
            className="w-full flex items-center justify-center gap-2 p-3 rounded-xl border bg-card border-border text-xs font-bold text-foreground hover:opacity-80 transition"
          >
            {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            <span>{theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}</span>
          </button>

          {/* CARD: DEVICE REAL-TIME STATUS */}
          <div className="p-4 sm:p-5 rounded-xl border bg-card border-border space-y-4 shadow-sm">
            <h4 className="text-xs font-bold uppercase tracking-wider text-foreground">
              DEVICE INFO
            </h4>

            <div className="flex items-center gap-3 p-3 rounded-lg border bg-primary/10 border-border">
              <span className="relative flex h-3 w-3 shrink-0">
                <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${status.is_online ? "bg-emerald-500" : "bg-rose-500"}`} />
                <span className={`relative inline-flex rounded-full h-3 w-3 ${status.is_online ? "bg-emerald-500" : "bg-rose-500"}`} />
              </span>
              <div>
                <div className={`text-xs font-extrabold flex items-center gap-1.5 text-foreground`}>
                  <Monitor className="w-3.5 h-3.5 stroke-[1.75]" />
                  <span className={status.is_online ? "" : "text-rose-400"}>
                    {status.is_online ? "CONNECTED" : "OFFLINE"}
                  </span>
                </div>
                <div className="text-[10px] font-medium text-muted-foreground">
                  Heartbeat 15s interval
                </div>
              </div>
            </div>

            <div className="space-y-2 text-xs text-foreground">
              <div className="flex justify-between border-b border-border/20 pb-1">
                <span className="font-medium text-muted-foreground">Device Name</span>
                <span className="font-bold">{deviceName}</span>
              </div>
              <div className="flex justify-between border-b border-border/20 pb-1">
                <span className="font-medium text-muted-foreground">Device ID</span>
                <span className="font-mono font-bold text-[10px] truncate max-w-[110px]">{deviceId}</span>
              </div>
              <div className="flex justify-between">
                <span className="font-medium text-muted-foreground">Last Heartbeat</span>
                <span className="text-[10px] font-mono font-bold">
                  {status.last_seen_at ? new Date(status.last_seen_at).toLocaleTimeString() : "N/A"}
                </span>
              </div>
            </div>
          </div>

          {/* DEVICE SELECTOR & ACCOUNT CARD */}
          <div className="p-4 sm:p-5 rounded-xl border bg-card border-border space-y-3 shadow-sm">
            <h4 className="text-xs font-bold uppercase tracking-wider text-foreground">
              ACCOUNT & DEVICES
            </h4>
            <div className="space-y-2 text-xs">
              <div className="p-2 rounded-md border bg-card border-border">
                <span className="text-[10px] font-medium text-muted-foreground">Login:</span>
                <div className="font-bold truncate text-foreground">{parentEmail}</div>
              </div>
              
              {allDevices.length > 1 && (
                <select
                  value={deviceId}
                  onChange={(e) => {
                    const dev = allDevices.find(d => d.device_id === e.target.value);
                    setDevice(e.target.value, dev?.device_name || "Agent PC");
                  }}
                  className="w-full p-2 text-xs font-bold rounded-md border bg-input border-border text-foreground focus:outline-none focus:border-primary"
                >
                  {allDevices.map(d => (
                    <option key={d.device_id} value={d.device_id}>
                      {d.device_name} {d.is_online ? "🟢" : "🔴"}
                    </option>
                  ))}
                </select>
              )}

              <button
                onClick={handleLogout}
                className="w-full py-2 flex items-center justify-center gap-2 text-xs font-bold rounded-md bg-danger-dark/20 border border-danger-dark/50 text-danger-light hover:bg-danger-dark/40 transition mt-2"
              >
                <LogOut className="w-4 h-4" />
                <span>LOGOUT</span>
              </button>
            </div>
          </div>

        </aside>
      </div>

      <MobileBottomNav 
        activeNav={location.pathname === '/' ? 'overview' : location.pathname.substring(1)} 
        setActiveNav={(nav) => navigate(nav === 'overview' ? '/' : `/${nav}`)} 
        userPermissions={userPermissions} 
      />
    </div>
  );
}

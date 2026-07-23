import { NavLink } from "react-router-dom";
import { ru } from "../i18n/ru";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `px-3 py-2 rounded text-sm font-medium ${isActive ? "bg-gray-900 text-white" : "text-gray-600 hover:bg-gray-100"}`;

export default function NavBar() {
  return (
    <nav className="flex items-center gap-2 border-b px-4 py-3">
      <span className="mr-4 text-lg font-bold">{ru.app.title}</span>
      <NavLink to="/campaigns" className={linkClass}>
        {ru.nav.campaigns}
      </NavLink>
      <NavLink to="/leads" className={linkClass}>
        {ru.nav.leads}
      </NavLink>
      <NavLink to="/settings" className={linkClass}>
        {ru.nav.settings}
      </NavLink>
    </nav>
  );
}

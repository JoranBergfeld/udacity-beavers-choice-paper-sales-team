import { NavLink } from "react-router-dom";

export default function Nav({ demo }: { demo: boolean }) {
  return (
    <nav className="nav">
      <div className="brand">
        📄 Munder Difflin <small>· The People Person's Paper People</small>
      </div>
      <span className="spacer" />
      <NavLink to="/" end>
        Reception
      </NavLink>
      <NavLink to="/reviews">Performance Reviews</NavLink>
      <NavLink to="/knowledge">Supply Closet</NavLink>
      <NavLink to="/setup">Setup</NavLink>
      {demo && <span className="badge-demo">DEMO MODE</span>}
    </nav>
  );
}

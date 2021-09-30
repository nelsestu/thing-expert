import React, { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { Nav, Navbar } from "react-bootstrap";
import Routes, { basename } from "./Routes";
import "./App.css";
import { AppContext } from "./libs/AppContext";
import { decodeJwt } from "./libs/Jwt";
import BasicError from "./libs/BasicError";

export default function App() {
  const [isAuthenticated, setAuthenticated] = useState(false);
  const [basicError, showBasicError] = useState(undefined);
  const location = useLocation();

  useEffect(() => {
    const session = decodeJwt(localStorage.getItem("session"));
    setAuthenticated(session && Date.now() < session.exp * 1000);
  }, []);

  async function handleLogout() {
    localStorage.clear();
    setAuthenticated(false);
  }

  const AppContextExports = {
    isAuthenticated,
    setAuthenticated,
    showBasicError,
  };

  return (
    <div className="App container">
      <Navbar bg="light">
        <Navbar.Brand href={`${basename}/`}>
          <span className="navbar-icon material-icons">developer_board</span>
          <span className="navbar-label">Baseline Manager</span>
        </Navbar.Brand>
        <Navbar.Collapse className="justify-content-end">
          <Nav>
            {isAuthenticated ? (
              <Nav.Link
                href={`${basename}/logout`}
                onClick={(e) => {
                  e.preventDefault();
                  handleLogout();
                }}
              >
                Logout
              </Nav.Link>
            ) : location.pathname !== "/login" ? (
              <Nav.Link href={`${basename}/login`}>Login</Nav.Link>
            ) : undefined}
          </Nav>
        </Navbar.Collapse>
      </Navbar>
      <AppContext.Provider value={AppContextExports}>
        <Routes />
        <BasicError
          details={basicError}
          onHide={async (error) => {
            showBasicError(undefined);
            if (error.logout === true) {
              await handleLogout();
            }
          }}
        />
      </AppContext.Provider>
    </div>
  );
}

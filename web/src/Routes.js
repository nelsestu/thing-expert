import React from "react";
import { useAppContext } from "./libs/AppContext";
import { Redirect, Route, Switch } from "react-router-dom";
import Welcome from "./containers/Welcome";
import Dashboard from "./containers/Dashboard";
import Login from "./containers/Login";
import NotFound from "./containers/NotFound";

export const basename =
  process.env.PUBLIC_URL +
  (process.env.REACT_APP_ROUTER_CLASS === "HashRouter" ? "/#" : "");

function AuthenticatedRoute({ children, ...attributes }) {
  const { isAuthenticated } = useAppContext();
  return (
    <Route {...attributes}>
      {isAuthenticated ? children : <Redirect to="/" />}
    </Route>
  );
}

function UnauthenticatedRoute({ children, ...attributes }) {
  const { isAuthenticated } = useAppContext();
  return (
    <Route {...attributes}>
      {!isAuthenticated ? children : <Redirect to="/dashboard" />}
    </Route>
  );
}

export default function Routes() {
  return (
    <Switch>
      <UnauthenticatedRoute exact path="/">
        <Welcome />
      </UnauthenticatedRoute>
      <UnauthenticatedRoute exact path="/login">
        <Login />
      </UnauthenticatedRoute>
      <AuthenticatedRoute exact path="/dashboard">
        <Dashboard />
      </AuthenticatedRoute>
      <Route component={NotFound} />
    </Switch>
  );
}

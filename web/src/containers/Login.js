import React, { useState } from "react";
import {
  Alert,
  Button,
  FormControl,
  FormGroup,
  FormLabel,
  Spinner,
} from "react-bootstrap";
import "./Login.css";
import { useAppContext } from "../libs/AppContext";
import { decodeJwt } from "../libs/Jwt";

export default function Login() {
  const [showDemoAlert, setShowDemoAlert] = useState(
    process.env.REACT_APP_API_URL === `${process.env.PUBLIC_URL}/demo`
  );
  const { setAuthenticated, showBasicError } = useAppContext();
  const [isLoading, setIsLoading] = useState(false);
  const [password, setPassword] = useState("");

  const sleep = (milliseconds) => {
    return new Promise((resolve) => setTimeout(resolve, milliseconds));
  };

  async function login() {
    const startAt = Date.now();

    setIsLoading(true);

    const response = await fetch(
      `${process.env.REACT_APP_API_URL}/v1/authenticate`,
      {
        method: "get",
        cache: "no-store",
        headers: new Headers({
          Authorization: btoa(password),
        }),
      }
    ).catch((e) => {
      return { ok: false };
    });

    const waitDiff = 1500 - (Date.now() - startAt);
    waitDiff > 0 && (await sleep(waitDiff));

    if (!response.ok) {
      setIsLoading(false);
      showBasicError({
        title: "Unable To Login!",
        body: (() => {
          switch (response.status) {
            case 401:
              return "Invalid password. Please try again.";
            case 500:
              return "Unexpected server error.";
            default:
              return "Unexpected error.";
          }
        })(),
      });
      return;
    }

    const jwt = await response.text();
    const session = decodeJwt(jwt);

    if (!session || Date.now() >= session.exp * 1000) {
      setIsLoading(false);
      showBasicError({
        title: "Unable To Login!",
        body: "Invalid session. Please login again.",
      });
      return;
    }

    localStorage.setItem("session", jwt);
    setAuthenticated(true);
  }

  return (
    <div className="Login">
      {showDemoAlert && (
        <Alert
          variant="primary"
          onClose={() => setShowDemoAlert(false)}
          dismissible
        >
          You are using Demo Mode. Any password below will be accepted.
        </Alert>
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          login();
        }}
      >
        <FormGroup controlId="iot-baseline-password">
          <FormLabel>Password</FormLabel>
          <FormControl
            autoFocus
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </FormGroup>
        <Button
          block
          type="submit"
          variant="primary"
          disabled={isLoading || password.length === 0}
        >
          {isLoading ? (
            <>
              <Spinner animation="grow" size="sm" className="spinner-1" />
              <Spinner animation="grow" size="sm" className="spinner-2" />
              <Spinner animation="grow" size="sm" className="spinner-3" />
            </>
          ) : (
            <span className="align-middle">Login</span>
          )}
        </Button>
      </form>
    </div>
  );
}

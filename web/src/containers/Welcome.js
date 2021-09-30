import React, { useState } from "react";
import "./Welcome.css";
import { Alert } from "react-bootstrap";

export default function Welcome() {
  const [showDemoAlert, setShowDemoAlert] = useState(
    process.env.REACT_APP_API_URL === `${process.env.PUBLIC_URL}/demo`
  );

  return (
    <div className="Welcome">
      {showDemoAlert && (
        <Alert
          variant="primary"
          onClose={() => setShowDemoAlert(false)}
          dismissible
        >
          You are using Demo Mode. Proceed to the login page and use any
          password to continue.
        </Alert>
      )}
      <h1>AWS IoT Baseline</h1>
      <p>An implementation starter kit.</p>
    </div>
  );
}

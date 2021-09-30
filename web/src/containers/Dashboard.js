import React, { useState } from "react";
import "./Dashboard.css";
import ThingsCard from "./ThingsCard.js";
import { Alert } from "react-bootstrap";

export default function Dashboard() {
  const [showDemoAlert, setShowDemoAlert] = useState(
    process.env.REACT_APP_API_URL === `${process.env.PUBLIC_URL}/demo`
  );

  return (
    <div className="Dashboard">
      {showDemoAlert && (
        <Alert
          variant="primary"
          onClose={() => setShowDemoAlert(false)}
          dismissible
        >
          You are using Demo Mode. The data displayed below is read from static
          files and written into browser storage. Any changes you make will only
          affect the browser storage. You can logout to reset the data.
        </Alert>
      )}
      <ThingsCard />
    </div>
  );
}

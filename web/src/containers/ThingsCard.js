import React, { useEffect, useRef, useState } from "react";
import {
  Accordion,
  Card,
  FormControl,
  InputGroup,
  Table,
} from "react-bootstrap";
import { useAppContext } from "../libs/AppContext";
import "./ThingsCard.css";

export default function ThingsCard() {
  const isRendered = useRef(true);

  const [things, setThings] = useState([]);
  const { isAuthenticated, showBasicError } = useAppContext();

  useEffect(() => {
    isAuthenticated && loadThings();
    return () => (isRendered.current = false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated]);

  async function loadThings(filter) {
    const response = await fetch(`${process.env.REACT_APP_API_URL}/v1/things`, {
      method: "get",
      headers: new Headers({
        Authorization: localStorage.getItem("session"),
      }),
    }).catch((e) => {
      return { ok: false };
    });

    if (!isRendered.current) return;

    if (!response.ok) {
      showBasicError({
        title: "Unable To Load Data!",
        body: (() => {
          switch (response.status) {
            case 401:
            case 403:
              return "Your session has expired. Please login again.";
            case 500:
              return "Unexpected server error.";
            default:
              return "Unexpected error.";
          }
        })(),
        logout: response.status === 401 || response.status === 403,
      });
      return;
    }

    const result = await response.json();

    if (result.things && filter) {
      filter = filter.toLowerCase();
      result.things = result.things.filter((thing) => {
        const displayName = thing.attributes && thing.attributes.name;
        return (
          (displayName && displayName.toLowerCase().includes(filter)) ||
          thing.name.toLowerCase().includes(filter)
        );
      });
    }

    setThings(result.things);
  }

  function renderThings() {
    return things.map((thing) => {
      return (
        <div key={`thing/${thing.name}`} className="list-group-item">
          <Accordion.Toggle
            as="div"
            className="thing-header"
            eventKey={thing.name}
          >
            <h5>{(thing.attributes && thing.attributes.name) || thing.name}</h5>
            {thing.attributes && thing.attributes.createdAt ? (
              <p>
                Created: {new Date(thing.attributes.createdAt).toLocaleString()}
              </p>
            ) : undefined}
          </Accordion.Toggle>
          <Accordion.Collapse eventKey={thing.name}>
            <div className="thing-details">
              <Table striped bordered hover size="sm">
                <thead>
                  <tr>
                    <th>Attribute</th>
                    <th>Value</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.keys(thing.attributes).map((key) => {
                    return (
                      <tr key={`attribute/${key}`}>
                        <td>
                          <input value={key} />
                        </td>
                        <td>{thing.attributes[key]}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </Table>
            </div>
          </Accordion.Collapse>
        </div>
      );
    });
  }

  return (
    <Card className="ThingsCard">
      <Card.Header>
        <InputGroup>
          <InputGroup.Prepend>
            <InputGroup.Text>Search</InputGroup.Text>
          </InputGroup.Prepend>
          <FormControl
            placeholder="All Things"
            onChange={(e) => loadThings(e.target.value)}
          />
        </InputGroup>
      </Card.Header>
      <Card.Body>
        {!things || things.length === 0 ? (
          <h5 className="empty-label">No Things Found</h5>
        ) : (
          <Accordion className="list-group list-group-flush">
            {renderThings()}
          </Accordion>
        )}
      </Card.Body>
    </Card>
  );
}

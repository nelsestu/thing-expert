import React from "react";
import { Button, Modal } from "react-bootstrap";

export default function BasicError(props) {
  const details = props.details;
  const onHide = () => props.onHide(details);
  return details ? (
    <Modal show={true} onHide={onHide}>
      <Modal.Header>
        <Modal.Title>{details.title}</Modal.Title>
      </Modal.Header>
      <Modal.Body>{details.body}</Modal.Body>
      <Modal.Footer>
        <Button variant="primary" onClick={onHide}>
          {details.close || "Close"}
        </Button>
      </Modal.Footer>
    </Modal>
  ) : null;
}

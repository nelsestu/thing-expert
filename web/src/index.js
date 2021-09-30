import React from "react";
import ReactDOM from "react-dom";
import { BrowserRouter, HashRouter } from "react-router-dom";
import "./index.css";
import App from "./App";
import { basename } from "./Routes";

console.log(`PUBLIC_URL = '${process.env.PUBLIC_URL}'`);
console.log(`REACT_APP_API_URL = '${process.env.REACT_APP_API_URL}'`);
console.log(`REACT_APP_ROUTER_CLASS = '${process.env.REACT_APP_ROUTER_CLASS}'`);

const [Router, RouterProps] = (() => {
  switch (process.env.REACT_APP_ROUTER_CLASS) {
    case "HashRouter":
      return [HashRouter, {}];
    default:
      return [BrowserRouter, { basename: basename }];
  }
})();

ReactDOM.render(
  <Router {...RouterProps}>
    <App />
  </Router>,
  document.getElementById("root")
);

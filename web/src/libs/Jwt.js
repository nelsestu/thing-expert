export function decodeJwt(token) {
  try {
    // https://stackoverflow.com/a/38552302
    let base64 = token.split(".")[1];
    base64 = base64.replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(
      decodeURIComponent(
        atob(base64)
          .split("")
          .map(function (c) {
            return "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2);
          })
          .join("")
      )
    );
  } catch {
    return null;
  }
}

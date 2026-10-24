export function openSandboxedPreview(previewWindow, url) {
  previewWindow.opener = null;

  const previewDocument = previewWindow.document;
  const frame = previewDocument.createElement("iframe");
  frame.setAttribute("sandbox", "");
  frame.title = "TrustVault document preview";
  frame.src = url;
  frame.style.width = "100vw";
  frame.style.height = "100vh";
  frame.style.border = "0";

  previewDocument.title = "TrustVault document preview";
  previewDocument.body.style.margin = "0";
  previewDocument.body.replaceChildren(frame);
}

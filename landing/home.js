// Sticky "How you use it" story: the step in the middle of the viewport drives the device on the left.
const steps = [...document.querySelectorAll(".steps li")];
const visuals = [...document.querySelectorAll(".story-visual .sv")];
const show = (n) => {
  steps.forEach((s) => s.classList.toggle("on", s.dataset.step === n));
  visuals.forEach((v) => v.classList.toggle("on", v.dataset.step === n));
};
show("0");
const io = new IntersectionObserver((entries) => {
  for (const e of entries) if (e.isIntersecting) show(e.target.dataset.step);
}, { rootMargin: "-45% 0px -45% 0px" });
steps.forEach((s) => io.observe(s));

// Hero: the selection rectangle frames exactly the rows LedgerFlow wrote, at every breakpoint.
const sheet = document.querySelector(".sheet"), heroSel = sheet?.querySelector(".sel");
const placeSel = () => {
  const rows = sheet.querySelectorAll("tr.new"); if (!rows.length) return;
  const box = sheet.getBoundingClientRect(), a = rows[0].cells[1].getBoundingClientRect(), z = rows[rows.length - 1].getBoundingClientRect();
  Object.assign(heroSel.style, { left: `${a.left - box.left}px`, right: "0px", top: `${a.top - box.top}px`, height: `${z.bottom - a.top}px` });
};
if (heroSel) { placeSel(); addEventListener("resize", placeSel); document.fonts?.ready.then(placeSel); }

// "Open the web app": the real LedgerFlow app with a demo workspace, no account or invite.
// Same server when this page is served at /welcome/ by the demo backend; otherwise the public origin in <meta name="ledgerflow-app">.
const appMeta = document.querySelector('meta[name="ledgerflow-app"]')?.content.trim();
const appBase = location.pathname.startsWith("/welcome/") ? location.origin : (appMeta || "").replace(/\/+$/, "");
document.querySelectorAll("[data-app-link]").forEach((a) => {
  if (!appBase) { a.hidden = true; return; }  // static copy without a backend: never send people to a dead link
  a.href = `${appBase}/?demo=${a.dataset.role}${a.dataset.hash || ""}`;
});
document.querySelectorAll("[data-app-note]").forEach((n) => { n.hidden = !appBase; });

// Sidebar toggle: desktop collapses; mobile opens drawer
const MOBILE_Q = "(max-width: 768px)";
function isMobile(){ return window.matchMedia(MOBILE_Q).matches; }

const desktopToggle = document.querySelector(".menu-toggle.container");
const fab = document.getElementById("globalMenuBtn");
const scrim = document.querySelector(".scrim");

function setAria(expanded){
  const v = expanded ? "true" : "false";
  if (desktopToggle) desktopToggle.setAttribute("aria-expanded", v);
  if (fab) fab.setAttribute("aria-expanded", v);
}

function openDrawer(){
  document.body.classList.add("nav-open");
  setAria(true);
  // Optional: move focus to first link in the sidebar for a11y
  const firstLink = document.querySelector(".sidebar nav a");
  if (isMobile() && firstLink) { try { firstLink.focus(); } catch {} }
}
function closeDrawer(){
  document.body.classList.remove("nav-open");
  setAria(false);
}

// Expose for inline handlers and other scripts
window.openDrawer = openDrawer;
window.closeDrawer = closeDrawer;

/* w3schools-style handler your file referenced */
function myFunction(el){
  // On mobile, treat the button as a drawer toggle; do NOT toggle 'sidebar-collapsed'
  if (isMobile()){
    if (document.body.classList.contains("nav-open")) closeDrawer();
    else openDrawer();
    // keep the visual 'change' state on the button that was clicked
    if (el) el.classList.toggle("change", document.body.classList.contains("nav-open"));
    return;
  }
  // Desktop: collapse/expand sidebar
  const collapsed = document.body.classList.toggle("sidebar-collapsed");
  if (el){
    el.classList.toggle("change", collapsed);
    el.setAttribute("aria-expanded", (!collapsed).toString());
  }
  // Optional: remember preference
  try { localStorage.setItem("sidebarCollapsed", collapsed ? "1" : "0"); } catch {}
}
window.myFunction = myFunction;

/* Close with scrim click and Escape */
if (scrim) scrim.addEventListener("click", closeDrawer);
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && document.body.classList.contains("nav-open")) {
    e.preventDefault();
    closeDrawer();
  }
});

/* Optional: show demo creds helper */
window.addEventListener("DOMContentLoaded", () => {
  const demoBtn = document.getElementById("demoBtn");
  const note = document.getElementById("demoNote");
  if (demoBtn){
    demoBtn.addEventListener("click", () => {
      const hidden = note?.hidden ?? true;
      if (note) note.hidden = !hidden;
      demoBtn.textContent = hidden ? "Hide demo accounts" : "Demo accounts";
    });
  }

  // Start collapsed on smaller desktops for more canvas space
  if (window.innerWidth < 1100 && !isMobile()){
    document.body.classList.add("sidebar-collapsed");
    setAria(false);
  } else if (isMobile()){
    // Ensure 'sidebar-collapsed' doesn't linger on mobile
    document.body.classList.remove("sidebar-collapsed");
  }
});

/* Keep states sane on resize */
let _rsz;
window.addEventListener("resize", () => {
  clearTimeout(_rsz);
  _rsz = setTimeout(() => {
    if (isMobile()){
      // Drawer mode: no desktop collapse state
      document.body.classList.remove("sidebar-collapsed");
      setAria(false);
    } else {
      // Ensure drawer is closed on desktop
      closeDrawer();
    }
  }, 120);
});
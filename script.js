<<<<<<< HEAD
document.addEventListener('DOMContentLoaded', () => {
    const toggleButton = document.querySelector('.sidebar-toggle');
    const header = document.querySelector('header');
    if (toggleButton && header) {
        toggleButton.addEventListener('click', () => {
            toggleButton.classList.toggle('change');
            header.classList.toggle('collapsed');
        });
    }
});
=======
// function toggleSidebar(button) {
//     button.classList.toggle("change");
//     document.querySelector("header").classList.toggle("collapsed");
// }
// document.getElementById("myButton").addEventListener("click", function() {
//     myFunction(this);
// });


/* Sidebar toggle: desktop collapses; mobile opens drawer */
function isMobile(){ return window.matchMedia("(max-width: 768px)").matches; }

function openDrawer(){
  document.body.classList.add("nav-open");
  const btn = document.querySelector(".menu-toggle.container");
  btn?.classList.add("change");
  btn?.setAttribute("aria-expanded","true");
}
function closeDrawer(){
  document.body.classList.remove("nav-open");
  const btn = document.querySelector(".menu-toggle.container");
  btn?.classList.remove("change");
  btn?.setAttribute("aria-expanded","false");
}

/* w3schools-style handler your file referenced */
function myFunction(el){
  const collapsed = document.body.classList.toggle("sidebar-collapsed");
  el.classList.toggle("change");
  el.setAttribute("aria-expanded", (!collapsed).toString());
  // On mobile, treat the sidebar like a drawer instead
  if (isMobile()){
    if (document.body.classList.contains("nav-open")) closeDrawer();
    else openDrawer();
  }
}
window.myFunction = myFunction;
window.closeDrawer = closeDrawer;

/* Optional: show demo creds helper */
window.addEventListener("DOMContentLoaded", () => {
  const demoBtn = document.getElementById("demoBtn");
  const note = document.getElementById("demoNote");
  if (demoBtn){
    demoBtn.addEventListener("click", () => {
      note.hidden = !note.hidden;
      demoBtn.textContent = note.hidden ? "Demo accounts" : "Hide demo accounts";
    });
  }

  // Start collapsed on smaller desktops for more canvas space
  if (window.innerWidth < 1100 && !isMobile()){
    document.body.classList.add("sidebar-collapsed");
    const btn = document.querySelector(".menu-toggle.container");
    btn?.setAttribute("aria-expanded","false");
  }
});
<<<<<<< Updated upstream
>>>>>>> Stashed changes
>>>>>>> 767d0288e2f9f5710c4bed93bcb29c3c10b682e0
=======
>>>>>>> Stashed changes

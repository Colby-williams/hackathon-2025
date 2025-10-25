function toggleSidebar(button) {
    button.classList.toggle("change");
    document.querySelector("header").classList.toggle("collapsed");
}
document.getElementById("myButton").addEventListener("click", function() {
    myFunction(this);
});
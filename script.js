function myFunction(x) {
    x.classList.toggle("change");
}
document.getElementById("myButton").addEventListener("click", function() {
    myFunction(this);
});

// =====================================
// TIC OPS - JAVASCRIPT
// =====================================

document.addEventListener("DOMContentLoaded", function () {

    console.log("TIC OPS est prêt !");

    // CONFIRMATION AVANT SUPPRESSION
    const deleteForms = document.querySelectorAll(
        'form[action*="/admin/delete/"]'
    );

    deleteForms.forEach(function (form) {
        form.addEventListener("submit", function (event) {
            const confirmation = confirm(
                "Veux-tu vraiment supprimer ce vêtement ?"
            );

            if (!confirmation) {
                event.preventDefault();
            }
        });
    });

});

// OUVRIR UNE PHOTO EN GRAND
function openProductImage(src, alt) {

    const modal = document.getElementById("imageModal");
    const modalImage = document.getElementById("modalImage");

    if (!modal || !modalImage) {
        return;
    }

    modalImage.src = src;
    modalImage.alt = alt || "Photo du vêtement";

    modal.classList.add("active");
    modal.setAttribute("aria-hidden", "false");

    document.body.style.overflow = "hidden";
}

// FERMER LA PHOTO
function closeProductImage() {

    const modal = document.getElementById("imageModal");
    const modalImage = document.getElementById("modalImage");

    if (!modal || !modalImage) {
        return;
    }

    modal.classList.remove("active");
    modal.setAttribute("aria-hidden", "true");

    modalImage.src = "";

    document.body.style.overflow = "";
}

// FERMER AVEC LA TOUCHE ÉCHAP
document.addEventListener("keydown", function (event) {

    if (event.key === "Escape") {
        closeProductImage();
    }

});


// TIC OPS - JAVASCRIPT

document.addEventListener("DOMContentLoaded", function () {

    console.log("TIC OPS est prêt !");

    // Confirmation avant suppression d'un vêtement
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

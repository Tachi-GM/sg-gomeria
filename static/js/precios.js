function cargarDatosTarea(boton) {
    document.getElementById('edit-id').value = boton.dataset.id;
    document.getElementById('edit-nombre').value = boton.dataset.nombre;
    document.getElementById('edit-precio1').value = boton.dataset.precio1;
    document.getElementById('edit-precio2').value = boton.dataset.precio2;
    document.getElementById('edit-precio3').value = boton.dataset.precio3;
}

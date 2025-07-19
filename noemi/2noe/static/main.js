
const form = document.getElementById("form-evento");
const lista = document.getElementById("lista-eventos");
const climaDiv = document.getElementById("clima");
const horaDiv = document.getElementById("hora");
const recBox = document.getElementById("recomendacion");
const recTexto = document.getElementById("texto-recomendacion");

function actualizarHora() {
  const ahora = new Date();
  horaDiv.textContent = "Hora: " + ahora.toLocaleTimeString();
}
setInterval(actualizarHora, 1000);
actualizarHora();

fetch("/clima?ciudad=Lima")
  .then(res => res.json())
  .then(data => {
    climaDiv.textContent = `Clima: ${data.desc} (${data.temp}°C)`;
  });

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const titulo = document.getElementById("titulo").value;
  const fecha = document.getElementById("fecha").value;
  const descripcion = document.getElementById("descripcion").value;

  fetch("/agregar_evento", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ titulo, fecha, descripcion })
  }).then(() => {
    form.reset();
    cargarEventos();
  });
});

function cargarEventos() {
  fetch("/eventos")
    .then(res => res.json())
    .then(eventos => {
      lista.innerHTML = "";
      eventos.forEach((ev, i) => {
        const li = document.createElement("li");
        li.className = "border rounded px-4 py-2 hover:bg-gray-50 cursor-pointer";
        li.innerHTML = `<strong>${ev.titulo}</strong><br>${ev.fecha}<br>${ev.descripcion}`;
        li.addEventListener("click", () => {
          fetch("/recomendar", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ descripcion: ev.descripcion })
          })
            .then(res => res.json())
            .then(data => {
              recBox.classList.remove("hidden");
              recTexto.textContent = data.recomendacion;
            });
        });
        lista.appendChild(li);
      });
    });
}
cargarEventos();

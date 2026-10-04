// Opens full-size photos in an overlay. Without JS, the links still open the image directly.
(() => {
  const links = [...document.querySelectorAll("a[data-full]")];
  if (!links.length || !window.HTMLDialogElement) return;

  const box = document.createElement("dialog");
  box.className = "lightbox";
  box.innerHTML =
    '<img alt=""><p></p>' +
    '<button class="prev" aria-label="Previous photo">‹</button>' +
    '<button class="next" aria-label="Next photo">›</button>' +
    '<button class="close" aria-label="Close">×</button>';
  document.body.append(box);
  const img = box.querySelector("img");
  const caption = box.querySelector("p");
  let index = 0;

  const show = (i) => {
    index = (i + links.length) % links.length;
    const link = links[index];
    img.src = link.href;
    img.alt = link.querySelector("img")?.alt ?? "";
    caption.textContent = link.dataset.caption ?? "";
  };

  links.forEach((link, i) =>
    link.addEventListener("click", (event) => {
      event.preventDefault();
      show(i);
      box.showModal();
    }),
  );
  box.querySelector(".prev").onclick = () => show(index - 1);
  box.querySelector(".next").onclick = () => show(index + 1);
  box.querySelector(".close").onclick = () => box.close();
  box.addEventListener("click", (event) => {
    if (event.target === box) box.close();
  });
  box.addEventListener("close", () => img.removeAttribute("src"));
  document.addEventListener("keydown", (event) => {
    if (!box.open) return;
    if (event.key === "ArrowLeft") show(index - 1);
    if (event.key === "ArrowRight") show(index + 1);
  });
  let touchX = null;
  box.addEventListener("touchstart", (event) => { touchX = event.touches[0].clientX; }, { passive: true });
  box.addEventListener("touchend", (event) => {
    if (touchX === null) return;
    const dx = event.changedTouches[0].clientX - touchX;
    touchX = null;
    if (Math.abs(dx) > 50) show(index + (dx < 0 ? 1 : -1));
  });
})();

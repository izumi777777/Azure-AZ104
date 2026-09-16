(function () {
  const fieldset = document.querySelector(".choices");
  if (!fieldset) return;
  const limit = Number(fieldset.dataset.selectCount || "1");
  if (limit <= 1) return;

  const boxes = Array.from(fieldset.querySelectorAll('input[type="checkbox"]'));
  boxes.forEach((box) => {
    box.addEventListener("change", () => {
      const checked = boxes.filter((item) => item.checked);
      if (checked.length > limit) {
        box.checked = false;
      }
    });
  });

})();

let currentGroup = [];
let currentIndex = 0;

document.querySelectorAll('.preview-img').forEach((img, idx, all) => {
  img.addEventListener('click', () => {
    currentGroup = Array.from(document.querySelectorAll(`.preview-img[data-group='${img.dataset.group}']`));
    currentIndex = currentGroup.indexOf(img);
    showPreview(currentGroup[currentIndex].src);
  });
});

function showPreview(src) {
  const previewImage = document.getElementById('previewImage');
  previewImage.src = src;
  const modal = new bootstrap.Modal(document.getElementById('imagePreviewModal'));
  modal.show();
}

function navigateImage(direction) {
  if (currentGroup.length === 0) return;
  currentIndex += direction;
  if (currentIndex < 0) currentIndex = currentGroup.length - 1;
  if (currentIndex >= currentGroup.length) currentIndex = 0;
  showPreview(currentGroup[currentIndex].src);
}
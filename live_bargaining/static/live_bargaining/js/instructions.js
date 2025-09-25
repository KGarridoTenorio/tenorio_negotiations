function updateSliderValue(element) {
  // Get the parent node of the slider, then find the spans within the next sibling div
  let displayDiv = element.nextElementSibling;
  let spans = displayDiv.getElementsByTagName('span');

  // Update the displayed current value
  if (spans.length >= 1) {
    spans[0].textContent = element.value;
  }

  // Only allow input of both sliders have been touched
  let acceptable = document.getElementById("acceptableProfit").textContent;
  let expected = document.getElementById("expectedProfit").textContent;
  if (acceptable !== "" && expected !== "") {
    document.getElementById("nextButton").disabled = false;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  // Only disable next button on pages with sliders
  let acceptable = document.getElementById("acceptableProfit");
  let expected = document.getElementById("expectedProfit");
  if (acceptable === null || expected === null) {
    document.getElementById("nextButton").disabled = false;
  }
});

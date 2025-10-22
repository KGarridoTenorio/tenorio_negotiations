////////////////////////////////////////////////////////////////////////////////
// Initialization
////////////////////////////////////////////////////////////////////////////////
const myPrice = document.getElementById('myPrice');
const myQuality = document.getElementById('myQuality');
const myQualityOut = document.getElementById('myQualityOut');
const myProposal = document.getElementById('my-proposal');
const otherProposal = document.getElementById('other-proposal');

const btnChat = document.getElementById("btn-chat");
const btnOffer = document.getElementById("btn-offer");
const btnAccept = document.getElementById('btn-accept');

// Decision Support System elements
const analysisPrice = document.getElementById('analysisPrice');
const analysisQuantity = document.getElementById('analysisQuantity');
const btnDisplayProfits = document.getElementById('btn-display-profits');
let profitLineChart = null;

document.addEventListener('DOMContentLoaded', () => {
  if (js_vars.bot_opponent === true) {
    // Disable send buttons for bot opponent
    btnChat.disabled = true;
    myPrice.disabled = true;
    myQuality.disabled = true;

    // Start the negotiations, needed here for event loop
    setTimeout(() => {
      liveSend({'type': 'initial'});
    }, 1000);
  }
  receiveMessage(js_vars.messages);
  receiveoffers(js_vars.offers);

  // Always disable offer button on (re)loading of page
  btnOffer.disabled = true;
  if (!otherProposal.innerHTML.includes('none')) {
    btnAccept.style.display = 'block';
  }

  // Set the timer color to red if 30 seconds left
  $('.otree-timer__time-left').on('update.countdown', function (event) {
    if (event.offset.totalSeconds <= 30) {
      document.getElementsByClassName('time-left')[0].style.color = "#FF0000";
    }
  });

  setInterval(() => {
    liveSend({'type': 'ping'});
  }, 1000);
  
  // Initialize Decision Support System
  initializeDecisionSupport();
});

function liveRecv(data) {
  if ('finished' in data) {
    document.getElementById('form').submit();
  }
  if ('chat' in data) {
    receiveMessage(data.chat);
  }
  if ('offers' in data) {
    receiveoffers(data.offers);
  }
  if ('unblock' in data) {
    console.log("UNBLOCK received!");
    blockUnblock(false);
  }
}

////////////////////////////////////////////////////////////////////////////////
// Decision Support System
////////////////////////////////////////////////////////////////////////////////
function initializeDecisionSupport() {
  // Add event listeners for analysis inputs
  if (analysisPrice && analysisQuantity && btnDisplayProfits) {
    analysisPrice.addEventListener('input', updateDisplayProfitsButton);
    analysisQuantity.addEventListener('input', updateDisplayProfitsButton);
    
    // Ensure button starts disabled
    btnDisplayProfits.disabled = true;
  } else {
    console.warn('DSS elements not found:', {
      analysisPrice: !!analysisPrice,
      analysisQuantity: !!analysisQuantity,
      btnDisplayProfits: !!btnDisplayProfits
    });
  }
}

function updateDisplayProfitsButton() {
  if (analysisPrice && analysisQuantity && btnDisplayProfits) {
    const priceValue = parseFloat(analysisPrice.value);
    const quantityValue = parseInt(analysisQuantity.value);
    
    if (!isNaN(priceValue) && !isNaN(quantityValue) && priceValue > 0 && quantityValue > 0) {
      btnDisplayProfits.disabled = false;
      btnDisplayProfits.style.backgroundColor = '#007bff';
      btnDisplayProfits.style.cursor = 'pointer';
    } else {
      btnDisplayProfits.disabled = true;
      btnDisplayProfits.style.backgroundColor = '#6c757d';
      btnDisplayProfits.style.cursor = 'not-allowed';
    }
  }
}

// Expected demand calculation based on quality (quantity) - same formula as before
function expectedDemandFromQuality(quality) {
  const demandMin = js_vars.demand_min || 0;
  const demandMax = js_vars.demand_max || 100;
  
  const numerator = ((quality * quality - demandMin * demandMin) / 2 + quality * (demandMax - quality));
  const denominator = (demandMax - demandMin);
  const demand = numerator / denominator;
  
  return Math.max(0, Math.min(demandMax, demand));
}

// Build profit data series for line chart
function buildProfitSeries(graph_price, graph_quantity) {
  const p = parseFloat(graph_price);
  const q = parseInt(graph_quantity);
  const marketPrice = js_vars.market_price || 11;
  const productionCost = js_vars.production_cost || 4;
  const demandMin = js_vars.demand_min || 0;
  const demandMax = js_vars.demand_max || 100;

  const demandAxis = [];
  const supplierProfits = [];
  const buyerProfits = [];

  // Generate profit data for each demand level
  for (let d = demandMin; d <= demandMax; d++) {
    const expectedSales = Math.min(q, d);
    
    // Correct profit formulas
    const supplierProfit = (p * expectedSales) - (productionCost * q);
    const buyerProfit = (marketPrice - p) * expectedSales;
    
    demandAxis.push(d);
    supplierProfits.push(supplierProfit);
    buyerProfits.push(buyerProfit);
  }

  // Calculate expected profits at expected demand point
  const expectedDemand = expectedDemandFromQuality(q);
  const expectedSales = Math.min(q, expectedDemand);
  const expectedSupplierProfit = (p * expectedSales) - (productionCost * q);
  const expectedBuyerProfit = (marketPrice - p) * expectedSales;

  return {
    demandAxis,
    supplierProfits,
    buyerProfits,
    expectedDemand,
    expectedSupplierProfit,
    expectedBuyerProfit
  };
}

// Main function called by the button - make it global
function plotProfitsVsDemand() {
  console.log('plotProfitsVsDemand called');
  
  if (!analysisPrice || !analysisQuantity) {
    alert('Analysis inputs not found! Please check the HTML.');
    return;
  }

  const priceValue = parseFloat(analysisPrice.value);
  const quantityValue = parseInt(analysisQuantity.value);

  console.log('Input values:', { priceValue, quantityValue });

  if (isNaN(priceValue) || isNaN(quantityValue) || priceValue <= 0 || quantityValue <= 0) {
    alert('Please enter valid positive values for price and quantity.');
    return;
  }

  const {
    demandAxis,
    supplierProfits,
    buyerProfits,
    expectedDemand,
    expectedSupplierProfit,
    expectedBuyerProfit
  } = buildProfitSeries(priceValue, quantityValue);

  const ctx = document.getElementById('profitLineChart');
  if (!ctx) {
    alert('Canvas element "profitLineChart" not found! Please check the HTML.');
    console.error('Canvas element profitLineChart not found!');
    return;
  }

  console.log('Creating chart with data points:', demandAxis.length);

  // Destroy existing chart if it exists
  if (profitLineChart) {
    profitLineChart.destroy();
  }

  profitLineChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: demandAxis,
      datasets: [
        {
          label: 'Supplier Profit',
          data: supplierProfits,
          borderColor: 'rgba(255, 99, 132, 1)',
          backgroundColor: 'rgba(255, 99, 132, 0.1)',
          borderWidth: 2,
          tension: 0.1,
          pointRadius: 0,
          fill: false
        },
        {
          label: 'Buyer Profit',
          data: buyerProfits,
          borderColor: 'rgba(54, 162, 235, 1)',
          backgroundColor: 'rgba(54, 162, 235, 0.1)',
          borderWidth: 2,
          tension: 0.1,
          pointRadius: 0,
          fill: false
        },
        // Expected profit horizontal lines (dashed)
        {
          label: 'E[π_Supplier]',
          data: demandAxis.map(() => expectedSupplierProfit),
          borderColor: 'rgba(255, 99, 132, 0.6)',
          backgroundColor: 'rgba(255, 99, 132, 0.1)',
          borderWidth: 1,
          borderDash: [6, 6],
          pointRadius: 0,
          fill: false
        },
        {
          label: 'E[π_Buyer]',
          data: demandAxis.map(() => expectedBuyerProfit),
          borderColor: 'rgba(54, 162, 235, 0.6)',
          backgroundColor: 'rgba(54, 162, 235, 0.1)',
          borderWidth: 1,
          borderDash: [6, 6],
          pointRadius: 0,
          fill: false
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false
      },
      plugins: {
        title: {
          display: true,
          text: `Profit vs Demand (Price: €${priceValue.toFixed(2)}, Quantity: ${quantityValue})`
        },
        legend: {
          display: true,
          position: 'bottom'
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              return `${context.dataset.label}: €${context.parsed.y.toFixed(2)}`;
            }
          }
        }
      },
      scales: {
        x: {
          title: {
            display: true,
            text: 'Demand'
          },
          grid: {
            color: 'rgba(0, 0, 0, 0.1)'
          }
        },
        y: {
          title: {
            display: true,
            text: 'Profit (€)'
          },
          grid: {
            color: 'rgba(0, 0, 0, 0.1)'
          },
          ticks: {
            callback: function(value) {
              return '€' + value;
            }
          }
        }
      }
    }
  });

  console.log('Chart created successfully');

  // Update profit details
  updateProfitDetails(priceValue, quantityValue, expectedDemand, expectedSupplierProfit, expectedBuyerProfit);
}

function updateProfitDetails(graph_price, graph_quantity, expectedDemand, expectedSupplierProfit, expectedBuyerProfit) {
  const detailsDiv = document.getElementById('profit-details');
  if (!detailsDiv) {
    console.warn('profit-details div not found');
    return;
  }
  
  const totalExpectedProfit = expectedSupplierProfit + expectedBuyerProfit;
  const supplierShare = totalExpectedProfit > 0 ? (Math.max(0, expectedSupplierProfit) / Math.max(1, Math.max(0, expectedSupplierProfit) + Math.max(0, expectedBuyerProfit))) * 100 : 0;
  
  let html = `
    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 10px;">
      <h5>Analysis for Price: €${graph_price.toFixed(2)}, Quantity: ${graph_quantity}</h5>
      <p><strong>Expected Demand:</strong> ${expectedDemand.toFixed(2)} units</p>
    </div>
    
    <div style="display: flex; gap: 20px; margin-bottom: 15px;">
      <div style="background-color: rgba(255, 99, 132, 0.1); padding: 10px; border-radius: 5px; flex: 1;">
        <h6 style="color: rgba(255, 99, 132, 1); margin-bottom: 5px;">Expected Supplier Profit</h6>
        <p style="font-size: 18px; font-weight: bold; margin: 0; color: ${expectedSupplierProfit < 0 ? '#dc3545' : 'inherit'};">
          €${expectedSupplierProfit.toFixed(2)}
        </p>
      </div>
      <div style="background-color: rgba(54, 162, 235, 0.1); padding: 10px; border-radius: 5px; flex: 1;">
        <h6 style="color: rgba(54, 162, 235, 1); margin-bottom: 5px;">Expected Buyer Profit</h6>
        <p style="font-size: 18px; font-weight: bold; margin: 0; color: ${expectedBuyerProfit < 0 ? '#dc3545' : 'inherit'};">
          €${expectedBuyerProfit.toFixed(2)}
        </p>
      </div>
    </div>
    
    <div style="background-color: #e9ecef; padding: 10px; border-radius: 5px;">
      <p><strong>Total Expected Profit:</strong> €${totalExpectedProfit.toFixed(2)}</p>
      ${totalExpectedProfit > 0 ? 
        `<p><strong>Supplier Share:</strong> ${supplierShare.toFixed(1)}%</p>` : 
        '<p style="color: orange;"><strong>Warning:</strong> No positive total expected profit.</p>'
      }
    </div>
  `;
  
  if (expectedSupplierProfit < 0 || expectedBuyerProfit < 0) {
    html += `
      <div style="background-color: #f8d7da; color: #721c24; padding: 10px; border-radius: 5px; margin-top: 10px;">
        <strong>⚠️ Warning:</strong> Negative expected profits detected. This deal may result in losses.
      </div>
    `;
  }
  
  detailsDiv.innerHTML = html;
}

////////////////////////////////////////////////////////////////////////////////
// Blocking functionality
////////////////////////////////////////////////////////////////////////////////
let blockedChat = js_vars.bot_opponent;
let blockedOffer = js_vars.bot_opponent;
let blockCount = 0;

function blockUnblock(block) {
  if (js_vars.bot_opponent !== true) {
    return;
  }

  blockedChat = btnChat.disabled = block;

  blockedOffer = block;
  if (blockedOffer === true) {
    btnOffer.disabled = true;
    myPrice.disabled = true;
    myQuality.disabled = true;
  } else {
    myPrice.disabled = false;
    myQuality.disabled = false;
    // Price has been entered, Quality has been entered
    if (myPrice.value !== "" && myQuality.value !== "") {
      btnOffer.disabled = false;
    }
  }
  myPrice.placeholder="Price here..."
}

function unblockAfterMessage() {
  if (js_vars.bot_opponent !== true) {
    return;
  }
  let nicks = chatOutput.getElementsByClassName('otree-chat__nickname');

  blockCount = 0;
  Array.from(nicks).forEach((n) => {
    blockCount += n.innerHTML.includes("(Me)");
  });

  let lastNick = nicks[nicks.length - 1].innerHTML;
  if (!lastNick.includes("(Me)")) {
    blockUnblock(false);
  }
}

////////////////////////////////////////////////////////////////////////////////
// Bargain functionality
////////////////////////////////////////////////////////////////////////////////
myPrice.addEventListener("keydown", function (event) {
  // Only allow numbers and Delete/Backspace
  let key = event.key;
  if (
    isNaN(parseFloat(key)) && // Allow numbers
    key !== "." &&          // Allow decimal point
    key !== "Delete" &&
    key !== "Backspace"
  ) {
    event.preventDefault();
    return;
  }

  // Prevent multiple decimal points
  if (key === "." && myPrice.value.includes(".")) {
      event.preventDefault();
      return;
    }

  // Prevent more than 2 decimal places
  if (myPrice.value.includes(".") && myPrice.value.split(".")[1].length >= 2 && key !== "Delete" && key !== "Backspace") {
    event.preventDefault();
    return;
  }

  if (myPrice.value.trim() !== "" && myQuality.value.trim() !== "" && blockedOffer === false) {
    btnOffer.disabled = false;
  } else {
    btnOffer.disabled = true;
  }

});

// Restrict quantity to integers only
myQuality.addEventListener("keydown", function (event) {
  // Allow only numbers, Delete, and Backspace
  let key = event.key;
  if (
    isNaN(parseInt(key)) && // Allow numbers
    key !== "Delete" &&
    key !== "Backspace"
  ) {
    event.preventDefault();
    return;
  }
  if (myPrice.value.trim() !== "" && myQuality.value.trim() !== "" && blockedOffer === false) {
    btnOffer.disabled = false;
  } else {
    btnOffer.disabled = true;
  }
});

// Restrict quantity to integers only and enforce min/max values
myQuality.addEventListener("input", function () {
  // Ensure the input is an integer
  myQuality.value = myQuality.value.replace(/[^0-9]/g, ""); // Remove non-numeric characters

  // Enforce minimum and maximum values
  if (myQuality.value !== "") {
    let value = parseInt(myQuality.value);
    if (value < 0) {
      myQuality.value = 0;
    } else if (value > 100) {
      myQuality.value = 100;
    }
  }
  if (myPrice.value.trim() !== "" && myQuality.value.trim() !== "" && blockedOffer === false) {
    btnOffer.disabled = false;
  } else {
    btnOffer.disabled = true;
  }
});

function sendOffer() {
  let price = parseFloat(myPrice.value);
  let quality = parseInt(myQuality.value);
  if (!isNaN(price) && !isNaN(quality)) {
    liveSend({'type': 'propose', 'price': price, 'quality': quality})
  }
  myPrice.value = "";
  myQuality.value = "";
  myQualityOut.innerHTML = "";
  btnOffer.disabled = true;
  blockUnblock(true);
}

function sendAccept() {
  btnChat.disabled = true;
  btnOffer.disabled = true;
  btnAccept.disabled = true;

  let proposal = otherProposal.innerHTML;
  let price = parseFloat(proposal.split('<br>')[0].replace('€', ''));
  if (isNaN(price)) {
    return;
  }
  let quality = parseInt(proposal.split('<br>')[1]);
  liveSend({'type': 'accept', 'price': price, 'quality': quality})
}

function receiveoffers(offers) {
  offers.forEach((offer) => {
    if (offer['price'] !== null && offer['quality'] !== null) {
      let innerHTML = `€ ${offer['price']}<br>${offer['quality']}`;
      if (offer['idx'] === js_vars.id_in_group) {
        myProposal.innerHTML = innerHTML;
      } else {
        otherProposal.innerHTML = innerHTML;
        btnAccept.style.display = 'block';
      }
    }
  });
}

////////////////////////////////////////////////////////////////////////////////
// Chat functionality
////////////////////////////////////////////////////////////////////////////////
const chatOutput = document.getElementById("chat-output");
const chatInput = document.getElementById("chat-input");

chatInput.addEventListener("keydown", function (event) {
  if (event.key === "Enter" && blockedChat === false) {
    sendMessage();
  }
});

function sendMessage() {
  let body = chatInput.value;
  if (body === "") {
    return;
  }

  liveSend({'type': 'chat', 'body': body});

  chatInput.value = "";
  blockUnblock(true);
}

function receiveMessage(messages) {
  let messagesHTML = '';
  messages.forEach((message) => {
    let nick = escapeHtml(message['nick']);
    let body = escapeHtml(message['body']).replaceAll('\n', '<br>');
    messagesHTML += "<div class='otree-chat__msg'>" +
        "<span class='otree-chat__nickname'>" + nick + "</span>" +
        "<span class='otree-chat__body'>" + body + "</span>" +
        "</div>";
  });
  messagesHTML += "<div class='otree-chat__msg'>&nbsp;</div>";
  chatOutput.innerHTML = messagesHTML;
  chatOutput.scrollTo({
    top: chatOutput.scrollHeight,
    left: 0,
    behavior: "smooth",
  });
  if (messages.length > 0) {
    unblockAfterMessage();
  }
}

function escapeHtml(string) {
  let entityMap = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
    '/': '&#x2F;',
    '`': '&#x60;',
    '=': '&#x3D;'
  };

  return String(string).replace(/[&<>"'`=\/]/g, function (s) {
    return entityMap[s];
  });
}
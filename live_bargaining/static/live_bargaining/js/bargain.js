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
let profitChart = null;

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
  if (analysisPrice && analysisQuantity) {
    analysisPrice.addEventListener('input', updateDisplayProfitsButton);
    analysisQuantity.addEventListener('input', updateDisplayProfitsButton);
  }
}

function updateDisplayProfitsButton() {
  if (analysisPrice && analysisQuantity && btnDisplayProfits) {
    const priceValue = parseFloat(analysisPrice.value);
    const quantityValue = parseInt(analysisQuantity.value);
    
    if (!isNaN(priceValue) && !isNaN(quantityValue) && priceValue > 0 && quantityValue > 0) {
      btnDisplayProfits.disabled = false;
    } else {
      btnDisplayProfits.disabled = true;
    }
  }
}

// Dynamic demand calculation based on quality (quantity)
function calculateDemand(quality) {
  const demandMin = js_vars.demand_min;
  const demandMax = js_vars.demand_max;
  
  // Formula: ((quality^2 - demand_min^2) / 2 + quality * (demand_max - quality)) / (demand_max - demand_min)
  const numerator = ((quality * quality - demandMin * demandMin) / 2 + quality * (demandMax - quality));
  const denominator = (demandMax - demandMin);
  const demand = numerator / denominator;
  
  // Ensure demand is within reasonable bounds
  return Math.max(0, Math.min(demandMax, demand));
}

function calculateProfits(price, quantity) {
  // Get parameters from Django template variables
  const marketPrice = js_vars.market_price;
  const productionCost = js_vars.production_cost;
  const isSupplier = js_vars.is_supplier;
  
  // Calculate dynamic demand based on quantity (quality)
  const expectedSales = calculateDemand(quantity);
  
  let myProfit, otherProfit;
  let myRole, otherRole;
  
  if (isSupplier) {
    // I am supplier, other is buyer
    // CORRECT FORMULAS:
    // profit_supplier = (price × expected_sales) - (production_cost × quality)
    // profit_buyer = (market_price - price) × expected_sales
    myProfit = (price * expectedSales) - (productionCost * quantity);
    otherProfit = (marketPrice - price) * expectedSales;
    myRole = "Supplier (You)";
    otherRole = "Buyer (Counterpart)";
  } else {
    // I am buyer, other is supplier
    // CORRECT FORMULAS:
    // profit_buyer = (market_price - price) × expected_sales
    // profit_supplier = (price × expected_sales) - (production_cost × quality)
    myProfit = (marketPrice - price) * expectedSales;
    otherProfit = (price * expectedSales) - (productionCost * quantity);
    myRole = "Buyer (You)";
    otherRole = "Supplier (Counterpart)";
  }
  
  return {
    myProfit: myProfit,
    otherProfit: otherProfit,
    myRole: myRole,
    otherRole: otherRole,
    expectedSales: expectedSales,
    marketPrice: marketPrice,
    productionCost: productionCost,
    demandMin: js_vars.demand_min,
    demandMax: js_vars.demand_max
  };
}

function displayProfits() {
  const priceValue = parseFloat(analysisPrice.value);
  const quantityValue = parseInt(analysisQuantity.value);
  
  if (isNaN(priceValue) || isNaN(quantityValue) || priceValue <= 0 || quantityValue <= 0) {
    alert('Please enter valid positive values for price and quantity.');
    return;
  }
  
  const profits = calculateProfits(priceValue, quantityValue);
  
  // Update profit chart
  updateProfitChart(profits);
  
  // Update profit details
  updateProfitDetails(profits, priceValue, quantityValue);
}

function updateProfitChart(profits) {
  const ctx = document.getElementById('profitChart');
  if (!ctx) return;
  
  // Destroy existing chart if it exists
  if (profitChart) {
    profitChart.destroy();
  }
  
  // Only show chart if there are positive total profits
  const totalProfit = profits.myProfit + profits.otherProfit;
  if (totalProfit <= 0) {
    ctx.getContext('2d').clearRect(0, 0, ctx.width, ctx.height);
    return;
  }
  
  // Handle negative profits for display
  const myProfitForChart = Math.max(0, profits.myProfit);
  const otherProfitForChart = Math.max(0, profits.otherProfit);
  
  profitChart = new Chart(ctx, {
    type: 'pie',
    data: {
      labels: [profits.myRole, profits.otherRole],
      datasets: [{
        data: [myProfitForChart, otherProfitForChart],
        backgroundColor: [
          'rgba(54, 162, 235, 0.8)',   // Blue for user
          'rgba(255, 99, 132, 0.8)'    // Red for counterpart
        ],
        borderColor: [
          'rgba(54, 162, 235, 1)',
          'rgba(255, 99, 132, 1)'
        ],
        borderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: {
          display: true,
          text: 'Expected Profits Distribution'
        },
        legend: {
          display: true,
          position: 'bottom'
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              const label = context.label || '';
              const value = context.parsed;
              const total = myProfitForChart + otherProfitForChart;
              const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : '0.0';
              return `${label}: €${value.toFixed(2)} (${percentage}%)`;
            }
          }
        }
      }
    }
  });
}

function updateProfitDetails(profits, price, quantity) {
  const detailsDiv = document.getElementById('profit-details');
  if (!detailsDiv) return;
  
  const totalProfit = profits.myProfit + profits.otherProfit;
  
  let html = `
    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 10px;">
      <h5>Analysis for Price: €${price.toFixed(2)}, Quantity: ${quantity}</h5>
    </div>
    
    <div style="display: flex; gap: 20px; margin-bottom: 15px;">
      <div style="background-color: rgba(54, 162, 235, 0.1); padding: 10px; border-radius: 5px; flex: 1;">
        <h6 style="color: rgba(54, 162, 235, 1); margin-bottom: 5px;">${profits.myRole}</h6>
        <p style="font-size: 18px; font-weight: bold; margin: 0; color: ${profits.myProfit < 0 ? '#dc3545' : 'inherit'};">
          €${profits.myProfit.toFixed(2)}
        </p>
      </div>
      <div style="background-color: rgba(255, 99, 132, 0.1); padding: 10px; border-radius: 5px; flex: 1;">
        <h6 style="color: rgba(255, 99, 132, 1); margin-bottom: 5px;">${profits.otherRole}</h6>
        <p style="font-size: 18px; font-weight: bold; margin: 0; color: ${profits.otherProfit < 0 ? '#dc3545' : 'inherit'};">
          €${profits.otherProfit.toFixed(2)}
        </p>
      </div>
    </div>
    
    <div style="background-color: #e9ecef; padding: 10px; border-radius: 5px;">
      <p><strong>Total Expected Profit:</strong> €${totalProfit.toFixed(2)}</p>
      ${totalProfit > 0 ? 
        `<p><strong>Your Share:</strong> ${((Math.max(0, profits.myProfit) / Math.max(1, Math.max(0, profits.myProfit) + Math.max(0, profits.otherProfit))) * 100).toFixed(1)}%</p>` : 
        '<p style="color: orange;"><strong>Warning:</strong> No positive total profit with these parameters.</p>'
      }
    </div>
  `;
  
  if (profits.myProfit < 0 || profits.otherProfit < 0) {
    html += `
      <div style="background-color: #f8d7da; color: #721c24; padding: 10px; border-radius: 5px; margin-top: 10px;">
        <strong>⚠️ Warning:</strong> Negative profits detected. This deal may result in losses for one or both parties.
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
    isNaN(parseInt(key)) && // Allow numbers
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
  let price = parseInt(myPrice.value);
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
  let price = parseInt(proposal.split('<br>')[0].replace('€', ''));
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
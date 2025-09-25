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

document.addEventListener('DOMContentLoaded', () => {
  if (js_vars.bot_opponent === true) {
    // Disable send buttons for bot opponent
    btnChat.disabled = true;

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

  // Only for testing
  receiveoffersTest(js_vars.offers);
  fillSelects();
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

  // Only for testing
  if ('offers' in data) {
    receiveoffersTest(data.offers);
  }
  if ('interactions' in data) {
    // receiveInteractions(data.interactions);
  }
  if ('trail' in data) {
    receiveTrail(data.trail);
  }
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

  blockedOffer = block || (blockCount < 2);
  if (blockedOffer === true) {
    btnOffer.disabled = true;
  } else {
    // Price has been entered, slider has been moved
    if (myPrice.value !== "" && myQualityOut.innerHTML !== "") {
      btnOffer.disabled = false;
    }
  }
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
  if (isNaN(parseInt(key)) && !(key === 'Delete' || key === 'Backspace')) {
    event.preventDefault();
    return;
  }

  // Slider has been moved
  if (myQualityOut.innerHTML !== "" && blockedOffer === false) {
    btnOffer.disabled = false;
  }
});

myQuality.addEventListener("mouseup", function () {
  // Price has been entered
  if (myPrice.value !== "" && blockedOffer === false) {
    btnOffer.disabled = false;
  }
  myQualityOut.innerHTML = myQuality.value;
})

function sendOffer() {
  let price = parseInt(myPrice.value);
  let quality = parseInt(myQuality.value);
  if (!isNaN(price)) {
    liveSend({'type': 'propose', 'price': price, 'quality': quality})
  }
  myPrice.value = "";
  myQuality.value = 2;
  myQualityOut.innerHTML = "";
  btnOffer.disabled = true;
  blockUnblock(true);
}

function sendAccept() {
  let proposal = otherProposal.innerHTML;
  let price = parseInt(proposal.split('<br>')[0].replace('€', ''));
  if (isNaN(price)) {
    return;
  }
  let quality = parseInt(proposal.split('<br>')[1]);
  liveSend({'type': 'accept', 'price': price, 'quality': quality})
}

function receiveoffers(offers) {
  // myProposal.innerHTML = '(none)<br> ';
  // otherProposal.innerHTML = '(none)<br> ';

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

////////////////////////////////////////////////////////////////////////////////
// Test specific
////////////////////////////////////////////////////////////////////////////////
let restartModal

function startReset() {
  restartModal = new bootstrap.Modal(document.getElementById('restartModal'), {
    keyboard: false
  });
  restartModal.show();
}

function sendReset() {
  let role = null;
  let radios = document.getElementsByName("human_role");
  radios.forEach((radio) => {
    if (radio.checked) {
      role = radio.value;
    }
  });
  if (role === null) {
    return;
  }

  let select = document.getElementById("cost-select");
  if (select.selectedIndex === 0) {
    return;
  }
  let cost = parseInt(select.value);

  select = document.getElementById("market-select");
  if (select.selectedIndex === 0) {
    return;
  }
  let market = parseInt(select.value);

  select = document.getElementById("greedy-select");
  if (select.selectedIndex === 0) {
    return;
  }
  let maxGreedy = select.value === 'true';

  liveSend({
    'type': 'reset',
    'role': role,
    'cost': cost,
    'market': market,
    'max_greedy': maxGreedy
  });

  document.getElementById("human_role_output").innerHTML = role;
  document.getElementById("production_cost_output").innerHTML = `${cost}`;
  document.getElementById("market_price_output").innerHTML = `${market}`;
  document.getElementById("max_greedy_output").innerHTML = `${maxGreedy}`;

  document.getElementById("interactions").innerHTML = "";
  document.getElementById("my-proposal").innerHTML = "";
  document.getElementById("other-proposal").innerHTML = "";

  restartModal.hide();

  setTimeout(() => {
    liveSend({'type': 'initial'});
  }, 1000);
}

function receiveoffersTest(offers) {
  let offersDiv = document.getElementById("offers");
  offersDiv.innerHTML = "";

  offers.forEach((offer) => {
    let idx = `${offer.idx}`.padStart(2);
    let date = new Date(offer.stamp * 1000).toLocaleString("nl-NL");
    let price = `${offer.price}`.padStart(2);
    let quality = `${offer.quality}`.padStart(2);
    let from_chat = `${offer.from_chat}`.padStart(5);
    let enhanced = offer.enhanced === null ? 'F' : 'T';
    let from = `${offer.test}`;
    let inner = `[${idx}] ${price}, ${quality} || ${offer.profit_bot} ${''
    }|| ${enhanced} || ${date} ${from}`;
    offersDiv.innerHTML += `<pre>${inner}</pre>`;
  });
}

function receiveInteractions(interactions) {
  let interactionDiv = document.getElementById("interactions");
  interactionDiv.innerHTML = "";

  interactions.forEach((interaction) => {
    let role = `${interaction.role}`.padEnd(6);
    let message = interaction.content.replaceAll('\n', ' ').substring(0, 100);
    let inner = `[${role}] ${message}`;
    interactionDiv.innerHTML += `<pre>${inner}</pre>`;
  });
}

function receiveTrail(trail) {
  let trailDiv = document.getElementById("interactions");
  if (trailDiv.innerHTML === "") {
    let ctx = '<pre><b>Offer</b>: (Price, Quality); <b>E</b>: Eval; ';
    ctx += '<b>I</b>: Invalid; ';
    ctx += '<b>Lx</b>: Loops; [Profit bot, Greedy, Evaluation]</pre><br>';
    trailDiv.innerHTML = ctx;
  }
  trailDiv.innerHTML += `<pre>${trail.replaceAll('\n', '<br>')}</pre>`;
}

function fillSelects() {
  let select = document.getElementById("cost-select");
  for (let cost = js_vars.production_cost_low;
       cost <= js_vars.production_cost_high; cost++) {
    let opt = document.createElement('option');
    opt.value = cost;
    opt.innerHTML = cost;
    select.appendChild(opt);
  }

  select = document.getElementById("market-select");
  for (let price = js_vars.market_price_low;
       price <= js_vars.market_price_high; price++) {
    let opt = document.createElement('option');
    opt.value = price;
    opt.innerHTML = price;
    select.appendChild(opt);
  }
}

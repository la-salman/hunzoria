/*
 * Hunzoria enquiry handling - static site, no backend.
 *
 * Every enquiry form on the site carries class="enquiry-form". On submit we
 * assemble the answers into a pre-filled WhatsApp message and hand the visitor
 * off to WhatsApp, then show thank-you.html.
 *
 * Why WhatsApp rather than a form endpoint: this site is deployed to Vercel as
 * static files, so there is no server to receive a POST (the template's
 * original sendemail.php could never run there). WhatsApp also happens to be
 * how trips in this region are actually booked.
 *
 * ---------------------------------------------------------------------------
 * WHATSAPP_NUMBER is the single source of truth for every wa.me link on the
 * site - the forms, the floating bubble, and the inline "message us" CTAs.
 * Change it here only; scripts/propagate.py stamps the no-JS fallback hrefs.
 *
 * Format: country code + number, digits only, no '+', no spaces, no leading 0.
 * Pakistan example: 0301 234 5678  ->  923012345678
 * ---------------------------------------------------------------------------
 */
(function () {
  "use strict";

  var WHATSAPP_NUMBER = "923115598884";
  var PLACEHOLDER_NUMBER = "923000000000";

  var FIELD_LABELS = {
    name: "Name",
    phone: "Phone",
    email: "Email",
    trip: "Trip",
    start_date: "Preferred dates",
    group_size: "Group size",
    message: "Notes"
  };
  var FIELD_ORDER = ["name", "phone", "email", "trip", "start_date", "group_size", "message"];

  function qs(name) {
    var m = new RegExp("[?&]" + name + "=([^&]*)").exec(window.location.search);
    return m ? decodeURIComponent(m[1].replace(/\+/g, " ")) : null;
  }

  /* "hunza-valley-explorer" -> "Hunza Valley Explorer" (fallback only; if the
     slug matches an <option> value we use that option's real label instead). */
  function titleise(slug) {
    return slug.replace(/-/g, " ").replace(/\b\w/g, function (c) {
      return c.toUpperCase();
    });
  }

  function collect(form) {
    var data = {};
    Array.prototype.forEach.call(form.elements, function (el) {
      if (!el.name || el.disabled || el.type === "submit") return;
      var value = (el.value || "").trim();
      if (value) data[el.name] = value;
    });

    /* Sidebar widgets on tour and destination pages name their subject with a
       data attribute rather than a select. */
    if (!data.trip) {
      var subject = form.getAttribute("data-tour") || form.getAttribute("data-destination");
      if (subject) data.trip = subject;
    }
    return data;
  }

  function buildMessage(data) {
    var lines = ["Hello Hunzoria, I would like to enquire about a trip.", ""];
    FIELD_ORDER.forEach(function (key) {
      if (data[key]) lines.push(FIELD_LABELS[key] + ": " + data[key]);
    });
    lines.push("", "Sent from " + window.location.href);
    return lines.join("\n");
  }

  function invalid(form) {
    var missing = null;
    Array.prototype.forEach.call(form.elements, function (el) {
      if (missing) return;
      if (el.required && !(el.value || "").trim()) missing = el;
    });
    return missing;
  }

  function onSubmit(event) {
    var form = event.target;
    event.preventDefault();

    var missing = invalid(form);
    if (missing) {
      missing.focus();
      if (typeof missing.reportValidity === "function") missing.reportValidity();
      return;
    }

    var url =
      "https://wa.me/" + WHATSAPP_NUMBER + "?text=" + encodeURIComponent(buildMessage(collect(form)));

    if (WHATSAPP_NUMBER === PLACEHOLDER_NUMBER) {
      /* Loud on staging, so nobody ships the placeholder by accident. */
      window.console && console.warn("[inquiry.js] WhatsApp number is still the placeholder.");
    }

    var opened = window.open(url, "_blank");
    if (opened) {
      window.location.href = "thank-you.html";
    } else {
      /* Pop-up blocked - go straight to WhatsApp so the enquiry is not lost. */
      window.location.href = url;
    }
  }

  /* Preselect a trip from ?tour=<slug> / ?activity=<slug>, so the cards on
     activities.html land people on a form that already knows what they clicked. */
  function prefillFromQuery() {
    var slug = qs("tour") || qs("activity");
    if (!slug) return;

    var select = document.querySelector('.enquiry-form [name="trip"]');
    if (select && select.tagName === "SELECT") {
      var matched = false;
      Array.prototype.forEach.call(select.options, function (option) {
        if (option.value === slug) {
          select.value = slug;
          matched = true;
        }
      });
      if (!matched) {
        var option = document.createElement("option");
        option.value = slug;
        option.textContent = titleise(slug);
        option.selected = true;
        select.appendChild(option);
      }
      return;
    }

    var text = document.querySelector('.enquiry-form [name="trip"]');
    if (text) text.value = titleise(slug);
  }

  /* The floating button ships with the placeholder number in its href so it
     still works with JS disabled; here we point it at whatever WHATSAPP_NUMBER
     currently is, so the number only has to be corrected in one place. */
  function syncFloatingButton() {
    var greeting = "Hello Hunzoria, I have a question about your trips.";
    var href =
      "https://wa.me/" + WHATSAPP_NUMBER + "?text=" + encodeURIComponent(greeting);
    /* Several per page: the fixed bubble, plus any inline "message us" CTAs. */
    Array.prototype.forEach.call(document.querySelectorAll("[data-wa-float]"), function (link) {
      link.setAttribute("href", href);
    });
  }

  function init() {
    Array.prototype.forEach.call(document.querySelectorAll(".enquiry-form"), function (form) {
      form.addEventListener("submit", onSubmit);
    });
    prefillFromQuery();
    syncFloatingButton();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

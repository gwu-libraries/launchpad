function showmore(id) {
    var objt = document.getElementById("toggle-"+id);
    var objb = document.getElementById("brief-"+id);
    var objf = document.getElementById("full-"+id);
    if(objf.style.display == 'block') {
        objf.style.display='none';
        objb.style.display='block';
        objt.innerHTML="<a href=javascript:showmore('1');>[+] Show</a>";
    } 
    else {
        objf.style.display='block';
        objb.style.display='none';
        objt.innerHTML="<a href=javascript:showmore('1');>[-] Hide</a>";
    }        
}

function toggle_visibility(tbid,lnkid) {
    if(document.all) {
        document.getElementById(tbid).style.display = document.getElementById(tbid).style.display == "block" ? "none" : "block";
    } else {
        document.getElementById(tbid).style.display = document.getElementById(tbid).style.display == "table" ? "none" : "table";
    }
    document.getElementById(lnkid).value = document.getElementById(lnkid).value == "[-] Hide " ? "[+] Show " : "[-] Hide ";

}

var newwindow;
function sms(url) {
    newwindow = window.open(url, 'name', 'height=590,width=400,toolbar=0,scrollbars=0,location=0,statusbar=0,menubar=0,resizable=0');
    if (window.focus) {
        newwindow.focus();
    };
}

function cittogtxt(elemid) {
    if ($(elemid).text() == 'Hide') {
        $(elemid).text('Show');
    } else {
        $(elemid).text('Hide');
    }
}

function check_availability() {
  $(".offer").each(function(i, e) {
    var offer = $(e);
    var bibid = offer.attr('id');
    // the id looks like offer-{bibid}
    bibid = bibid.split('-')[1];
    var url = '/availability?bibid=' + bibid;
    $.ajax(url).done(add_availability);
  });
}

function add_availability(availability) {
  if (availability.summon) {
    var id = availability.summon;
  } else {
    var id = availability.wrlc;
  }

  // tally the number of items per location
  var locations = {};
  var callnumbers = {};
  for (var i = 0; i < availability.offers.length; i++) {
    a = availability.offers[i];
    var loc = a.availabilityAtOrFrom;
    if (! locations[loc]) {
      locations[loc] = 0
    }
    if (a.status == "http://schema.org/InStock") {
      locations[loc] += 1;
    } else if (a.status == "http://schema.org/InStoreOnly") {
      locations[loc] += 1;
    } else if (a.availabilityStarts == '2382-12-31') {
      locations[loc] += 1;
    }
    callnumbers[loc] = a.sku;
  }

  var offer = $("#offer-" + id);

  var locationCount = 0;
  for (loc in locations) {
    locationCount += 1;
    if (locationCount > 1) {
      var o = offer.clone();
      offer.after(o);
      offer = o;
    }
    if (locations[loc] > 1) {
      offer.find(".availability").append("(" + locations[loc] + ")");
    }
    offer.find('span[itemprop="availabilityAtOrFrom"]').text(loc + ' ' + callnumbers[loc]);
  }

}

$(document).ready(function() {

    $('#cover-image').load(function() {
        if ($('#cover-image').width() == 1) {
            $('#cover').toggle(200);
        };
        $(".item_body").hide();
        $(".item_head").click(function() {
            $(this).next(".item_body").slideToggle(250);
         });
    });

    $('img.cover-thumbnail').load(function(e) {
        var img = $(this);
        // sometimes summon api returns empty images with this width
        if (img.width() != 99.79999995231628) {
            $(this).show();
            $(this).parents("article").css("min-height", "80px");
        }
    });

    $("#citation_toggle").click(function() {
        $("#citation_data").toggle('fast', function() { });
        cittogtxt("#citation_toggle");
    });

    check_availability();
});

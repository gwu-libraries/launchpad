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

  // first we need to collect up some of the availability information
  // by location so we can have single lines for multiple items at the
  // same location
  
  var locations = {};
  var callnumbers = {};
  var descriptions = {}
  for (var i = 0; i < availability.offers.length; i++) {
    a = availability.offers[i];
    var loc = a.availabilityAtOrFrom;
    if (! locations[loc]) {
      locations[loc] = 0
    }
    if (a.availability == "http://schema.org/InStock" || 
        a.availability == "http://schema.org/InStoreOnly") {
      locations[loc] += 1;
    }
    callnumbers[loc] = a.sku;
    descriptions[loc] = a.description;
  }

  // get the offer element on the page

  if (availability.summon) {
    var offer = $('#offer-' + availability.summon);
  } else {
    var offer = $('#offer-' + availability.wrlc);
  }

  // if no availability information was available then hide the offer
  if (availability.offers.length == 0) {
    offer.hide();
  }

  // update the offer with the availability information
  
  var locationCount = 0;
  for (loc in locations) {
    
    // if there are more than one locations then the original needs to 
    // be copied and added to the DOM so we can have a separate line 
    // for each unique location
    
    locationCount += 1;
    if (locationCount > 1) {
      var o = offer.clone();
      o.attr('id', o.attr('id') + '-' + locationCount);
      offer.after(o);
      offer = o;
    }

    if (locations[loc] > 1) {
      var il = '(' + locations[loc] + ')';
      offer.find('span[itemprop="description"]').text('Available');
    } else {
      offer.find('span[itemprop="description"]').text(descriptions[loc]);
    }

    offer.find('span[itemprop="availabilityAtOrFrom"]').text(loc);

    if (callnumbers[loc]) {
      offer.find('span[itemprop="sku"]').text(callnumbers[loc]);
    }

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

<!-- placeholder non-html5 fix -->        
$(document).ready(function(){
        
  $('[placeholder]').focus(function() {
    var input = $(this);
    if (input.val() == input.attr('placeholder')) {
      input.val('');
      input.removeClass('placeholder');
    }
  }).blur(function() {
    var input = $(this);
    if (input.val() == '' || input.val() == input.attr('placeholder')) {
      input.addClass('placeholder');
      input.val(input.attr('placeholder'));
     }
  }).blur();
  $('[placeholder]').parents('form').submit(function() {
    $(this).find('[placeholder]').each(function() {
      var input = $(this);
      if (input.val() == input.attr('placeholder')) {
        input.val('');
      }
    });
  });

  $('#online').click(function() {
    $('#search').submit();
  });
        
});

<!-- toggle Show/Hide for subjects -->
$(document).ready(function(){

  $('.subjectsList').click(function(){
    $(this).text(function(i,currentcontent){
      return currentcontent == '[+] Show' ?  '[-] Hide' : '[+] Show';
    });
  });
});        

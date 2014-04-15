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
    $(".search-result").each(function(i, e) {
      var result = $(e);
    });
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
    $("#citation_toggle").click(function() {
        $("#citation_data").toggle('fast', function() { });
        cittogtxt("#citation_toggle");
    });
    check_availability();
});

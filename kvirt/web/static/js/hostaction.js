function hostenable(client){
  $("#wheel").show();
  $.ajax({  
       type: "POST",
        url: `/hosts/${client}/enable`,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Enable succeeded!!!" }, type: 'success'}).show(); 
                hoststable();
            } else {
                $('.top-right').notify({message: { text: "Enable  because of "+data.reason }, type: 'danger'}).show(); 
            };
		}
	});
}


function hostdisable(client){
  $("#wheel").show();
  $.ajax({  
       type: "POST",
        url: `/hosts/${client}/disable`,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Disable succeeded!!!" }, type: 'success'}).show(); 
                hoststable();
            } else {
                $('.top-right').notify({message: { text: "Disable Failed because of "+data.reason }, type: 'danger'}).show(); 
            };
		}
	});
}

function hostswitch(client){
  $("#wheel").show();
  $.ajax({  
       type: "POST",
        url: `/hosts/${client}/switch`,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Switch succeeded!!!" }, type: 'success'}).show(); 
                hoststable();
            } else {
                $('.top-right').notify({message: { text: "Switch Failed because of "+data.reason }, type: 'danger'}).show(); 
            };
		}
	});
}

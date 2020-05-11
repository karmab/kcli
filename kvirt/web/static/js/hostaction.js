function hostaction(client, action){
  $("#wheel").show();
  data = {'name': client, 'action': action};
  $.ajax({  
       type: "POST",
        url: '/hostaction',
        data: data,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Action "+action+" succeeded!!!" }, type: 'success'}).show(); 
                hoststable();
            } else {
                $('.top-right').notify({message: { text: "Action "+action+" Failed because of "+data.reason }, type: 'danger'}).show(); 
            };
		}
	});
}




function containerstart(container){
  $("#wheel").show();
  data = {'name': container, 'action': 'start'};
  $.ajax({  
       type: "POST",
        url: '/containeraction',
        data: data,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Container "+container+" Started!!!" }, type: 'success'}).show(); 
            } else {
                $('.top-right').notify({message: { text: "Container "+container+" Failed to Start" }, type: 'danger'}).show(); 
            };
		}
	});
}

function containerstop(container){
  $("#wheel").show();
  data = {'name': container, 'action': 'stop'};
  $.ajax({  
       type: "POST",
        url: '/containeraction',
        data: data,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Container "+container+" Stopped!!!" }, type: 'success'}).show(); 
            } else {
                $('.top-right').notify({message: { text: "Container "+container+" Failed to Stop" }, type: 'danger'}).show(); 
            };
		}
	});
}

function containerdelete(container){
  $("#wheel").show();
  data = {'name': container, 'action': 'delete'};
  $.ajax({
       type: "POST",
        url: '/containeraction',
        data: data,
        success: function(data) {
            $("#wheel").hide();
            if (data == '0') {
                $('.top-right').notify({message: { text: "Container "+container+" Deleted!!!" }, type: 'success'}).show();
            } else {
                $('.top-right').notify({message: { text: "Container "+container+" Failed to Delete" }, type: 'danger'}).show();
            };
        }
    });
}

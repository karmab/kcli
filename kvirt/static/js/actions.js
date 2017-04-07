function start(vm){
  $("#wheel").show();
  data = {'name': vm, 'action': 'start'};
  $.ajax({  
       type: "POST",
        url: '/vmaction',
        data: data,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Vm "+vm+" Started!!!" }, type: 'success'}).show(); 
            } else {
                $('.top-right').notify({message: { text: "VM "+vm+" Failed to Start" }, type: 'danger'}).show(); 
            };
		}
	});
}

function stop(vm){
  $("#wheel").show();
  data = {'name': vm, 'action': 'stop'};
  $.ajax({  
       type: "POST",
        url: '/vmaction',
        data: data,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Vm "+vm+" Stopped!!!" }, type: 'success'}).show(); 
            } else {
                $('.top-right').notify({message: { text: "VM "+vm+" Failed to Stop" }, type: 'danger'}).show(); 
            };
		}
	});
}

function kill(vm){
  $("#wheel").show();
  data = {'name': vm, 'action': 'delete'};
  $.ajax({
       type: "POST",
        url: '/vmaction',
        data: data,
        success: function(data) {
            $("#wheel").hide();
            if (data == '0') {
                $('.top-right').notify({message: { text: "Vm "+vm+" Deleted!!!" }, type: 'success'}).show();
            } else {
                $('.top-right').notify({message: { text: "VM "+vm+" Failed to Delete" }, type: 'danger'}).show();
            };
        }
    });
}

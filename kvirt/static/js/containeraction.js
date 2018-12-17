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
                containerstable();
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
                containerstable();
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
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Container "+container+" Deleted!!!" }, type: 'success'}).show();
                containerstable();
            } else {
                $('.top-right').notify({message: { text: "Container "+container+" Failed to Delete because "+data.reason }, type: 'danger'}).show();
            };
        }
    });
}

function containercreate(){
  name = $("#name").val();
  profile = $("#profile").val();
  $("#wheel").show();
  data = {'name': name, 'action': 'create', 'profile': profile};
  $.ajax({
       type: "POST",
        url: '/containeraction',
        data: data,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                if ( name == '' ) {
                name = data.container
                }
                $('.top-right').notify({message: { text: "Container "+name+" created!!!" }, type: 'success'}).show();
            } else {
                $('.top-right').notify({message: { text: "Container "+name+" not created because "+data.reason }, type: 'danger'}).show();
            };
        }
    });
}

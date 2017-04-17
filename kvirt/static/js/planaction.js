function planstart(plan){
  $("#wheel").show();
  data = {'name': plan, 'action': 'start'};
  $.ajax({  
       type: "POST",
        url: '/planaction',
        data: data,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Plan "+plan+" Started!!!" }, type: 'success'}).show(); 
            } else {
                $('.top-right').notify({message: { text: "VM "+plan+" Failed to Start" }, type: 'danger'}).show(); 
            };
		}
	});
}

function planstop(plan){
  $("#wheel").show();
  data = {'name': plan, 'action': 'stop'};
  $.ajax({  
       type: "POST",
        url: '/planaction',
        data: data,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Plan "+plan+" Stopped!!!" }, type: 'success'}).show(); 
            } else {
                $('.top-right').notify({message: { text: "VM "+plan+" Failed to Stop" }, type: 'danger'}).show(); 
            };
		}
	});
}

function plandelete(plan){
  $("#wheel").show();
  data = {'name': plan, 'action': 'delete'};
  var r = confirm("Are you sure you want to delete this Plan?");
  if (r != true) {
    return ;
  }
  $.ajax({
       type: "POST",
        url: '/planaction',
        data: data,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Plan "+plan+" Deleted!!!" }, type: 'success'}).show();
            } else {
                $('.top-right').notify({message: { text: "VM "+plan+" Failed to Delete because of"+ data.reason }, type: 'danger'}).show();
            };
        }
    });
}

function plancreate(name, url, planfile, deploy){
  $("#wheel").show();
  data = {'action': 'create', 'name': name, 'url': url, 'planfile': planfile, 'deploy': deploy};
  $.ajax({
       type: "POST",
        url: '/planaction',
        data: data,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Plan "+name+" Created!!!" }, type: 'success'}).show();
            } else {
                $('.top-right').notify({message: { text: "Plan "+name+" Failed to Create because "+data.reason }, type: 'danger'}).show();
            };
        }
    });
}

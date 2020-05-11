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
                $('.top-right').notify({message: { text: "Plan "+plan+" stopped!!!" }, type: 'success'}).show(); 
            } else {
                $('.top-right').notify({message: { text: "VM "+plan+" not stopped" }, type: 'danger'}).show(); 
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
                $('.top-right').notify({message: { text: "Plan "+plan+" deleted!!!" }, type: 'success'}).show();
                planstable();
            } else {
                $('.top-right').notify({message: { text: "VM "+plan+" not deleted because "+ data.reason }, type: 'danger'}).show();
            };
        }
    });
}

function plancreate(name, url){
  if (name === undefined) {
  name = $("#name").val();
  }
  if (url === undefined) {
  url = $("#planurl").val();
  }
  $("#wheel").show();
  data = {'action': 'create', 'name': name, 'url': url};
  $.ajax({
       type: "POST",
        url: '/planaction',
        data: data,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                if ( name == '' ) {
                  name = data.plan
                }
                $('.top-right').notify({message: { text: "Plan "+name+" created!!!" }, type: 'success'}).show();
            } else {
                $('.top-right').notify({message: { text: "Plan "+name+" Failed to Create because "+data.reason }, type: 'danger'}).show();
            };
        }
    });
}

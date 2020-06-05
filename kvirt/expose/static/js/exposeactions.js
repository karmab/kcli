function exposedelete(plan){
  $("#wheel").show();
  data = {'name': plan};
  var r = confirm("Are you sure you want to delete this Plan?");
  if (r != true) {
    return ;
  }
  $.ajax({
       type: "POST",
        url: '/exposedelete',
        data: data,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Plan "+plan+" deleted!!!" }, type: 'success'}).show();
            } else {
                $('.top-right').notify({message: { text: "VM "+plan+" not deleted because "+ data.reason }, type: 'danger'}).show();
            };
        }
    });
}

//function exposecreate(name){
//  $("#wheel").show();
//  data = {'name': name};
//  $.ajax({
//       type: "POST",
//        url: '/exposecreate',
//        data: data,
//        success: function(data) {
//            $("#wheel").hide();
//            if (data.result == 'success') {
//                if ( name == '' ) {
//                  name = data.plan
//                }
//                $('.top-right').notify({message: { text: "Plan "+name+" created!!!" }, type: 'success'}).show();
//            } else {
//                $('.top-right').notify({message: { text: "Plan "+name+" Failed to Create because "+data.reason }, type: 'danger'}).show();
//            };
//        }
//    });
//}

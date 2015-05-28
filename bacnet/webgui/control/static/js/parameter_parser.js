(function($){
  $.getQuery = function(query, pageurl) {
    if (!pageurl) {
      pageurl = window.location.href;
    }

    query = query.replace(/[\[]/,"\\\[").replace(/[\]]/,"\\\]");

    var expr = "[\\?&]"+query+"=([^&#]*)";
    var regex = new RegExp(expr);
    var results = regex.exec(pageurl);

    if( results !== null ) {
      return results[1];
    }

    return false;
  };
})(jQuery);

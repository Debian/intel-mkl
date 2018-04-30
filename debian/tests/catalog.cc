#include <iostream>
#include <cstdio>
#include <cstdlib>

#include <nl_types.h>

// This is used to test if we'are installing the message catalog to the
// right place.

int
main(void)
{
	{
		std::cout << "By absolute path" << std::endl;
		std::string name = "/usr/share/locale/en_US/mkl_msg.cat";
		nl_catd mkl_cat = catopen(name.c_str(), NL_CAT_LOCALE);
		perror("catopen");
		catclose(mkl_cat);
	}
	{
		std::cout << "By filename" << std::endl;
		// upstream use mklvars.sh script to export these ENV.
		setenv("NLSPATH", "/usr/share/locale/en_US/%N", 1);
		std::string name = "mkl_msg.cat";
		nl_catd mkl_cat = catopen(name.c_str(), NL_CAT_LOCALE);
		perror("catopen");
		catclose(mkl_cat);
	}
	return 0;
}

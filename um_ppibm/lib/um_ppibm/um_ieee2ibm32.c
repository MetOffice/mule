/**********************************************************************/
/* (C) Crown copyright Met Office. All rights reserved.               */
/* For further details please refer to the file LICENCE.txt           */
/* which you should have received as part of this distribution.       */
/* *****************************COPYRIGHT******************************/
/*                                                                    */
/* This file is part of the SHUMlib packing library extension module  */
/* for Mule.                                                          */
/*                                                                    */
/* Mule is free software: you can redistribute it and/or modify it    */
/* under the terms of the Modified BSD License, as published by the   */
/* Open Source Initiative.                                            */
/*                                                                    */
/* Mule is distributed in the hope that it will be useful,            */
/* but WITHOUT ANY WARRANTY; without even the implied warranty of     */
/* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the      */
/* Modified BSD License for more details.                             */
/*                                                                    */
/* You should have received a copy of the Modified BSD License        */
/* along with Mule.                                                   */
/* If not, see <http://opensource.org/licenses/BSD-3-Clause>.         */
/* ********************************************************************/

#ifndef NPY_1_7_API_VERSION
#define NPY_1_7_API_VERSION 0x00000007
#endif

#ifndef NPY_NO_DEPRECATED_API
#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION
#endif

#include <Python.h>
#include <numpy/arrayobject.h>
#include "c_shum_data_conv.h"
#include "c_shum_byteswap.h"
#include "c_shum_data_conv_version.h"

#if PY_MAJOR_VERSION >= 3
#define PyInt_FromLong PyLong_FromLong
#define MOD_ERROR_VAL NULL
#define MOD_SUCCESS_VAL(val) val
#define MOD_INIT(name) PyMODINIT_FUNC PyInit_##name(void)
#define MOD_DEF(ob, name, doc, methods)               \
  static struct PyModuleDef moduledef = {             \
    PyModuleDef_HEAD_INIT, name, doc, -1, methods, }; \
  ob = PyModule_Create(&moduledef);
#else
#define MOD_ERROR_VAL
#define MOD_SUCCESS_VAL(val)
#define MOD_INIT(name) PyMODINIT_FUNC init##name(void)
#define MOD_DEF(ob, name, doc, methods)               \
  ob = Py_InitModule3(name, methods, doc);
#endif

MOD_INIT(um_packing);

static PyObject *ieee2ibm32_py(PyObject *self, PyObject *args);
static PyObject *get_shumlib_version_py(PyObject *self, PyObject *args);

MOD_INIT(um_ieee2ibm32)
{
  PyDoc_STRVAR(um_ieee2ibm32__doc__,
  "This extension module provides access to the SHUMlib data conversions\n"
  "library.\n"
  );

  PyDoc_STRVAR(ieee2ibm32__doc__,
  "Converts a numpy array to a byte-string containing 32-bit byte-swapped \n"
  "words in IBM number format \n\n."
  "Usage:\n"
  "   um_ieee2ibm32.ieee2ibm32(array) \n\n"
  "Args:\n"
  "* array - A numpy.ndarray.\n"
  "Returns:\n"
  "  Byte-array/stream (suitable to write straight to file).\n"
  );

  PyDoc_STRVAR(get_shumlib_version__doc__,
  "Returns the SHUMlib version number used the compile the library.\n\n"
  "Returns:\n"
  "* version - The version number as an integer in YYYYMMX format.\n"
  );

  static PyMethodDef um_ieee2ibm32Methods[] = {
    {"ieee2ibm32", ieee2ibm32_py, METH_VARARGS, ieee2ibm32__doc__},
    {"get_shumlib_version", get_shumlib_version_py, 
                            METH_VARARGS, get_shumlib_version__doc__},
    {NULL, NULL, 0, NULL}
  };

  PyObject *mod;
  MOD_DEF(mod, "um_ieee2ibm32", um_ieee2ibm32__doc__, um_ieee2ibm32Methods);
  if (mod == NULL)
    return MOD_ERROR_VAL;

  import_array();
  return MOD_SUCCESS_VAL(mod);
}

////////////////////////////////////////////////////////////////////////////////

static PyObject *ieee2ibm32_py(PyObject *self, PyObject *args)
{
  // Setup and obtain inputs passed from python
  PyArrayObject *datain_obj;
  // Note the argument descriptor "O":
  //   - O  a python object (here a numpy.ndarray)
  if (!PyArg_ParseTuple(args, "O",
                        &datain_obj )) return NULL;

  // Cast self to void to avoid unused paramter errors
  (void) self;

  // Find out the datatype of the array to setup the arguments
  // to the conversion
  int datain_type = PyArray_TYPE(datain_obj);

  c_shum_datatypes data_type;

  // Someday we may want to be able to control these, but for
  // now they will be disabled
  int64_t offset = 0;
  int64_t stride = 1;
  int64_t size_in;

  // Size in depends on the object passed in
  switch(datain_type) {
  case NPY_FLOAT64:
    data_type = C_SHUM_REAL;
    size_in = 64;
    break;
  case NPY_INT64:
    data_type = C_SHUM_INTEGER;
    size_in = 64;
    break;
  case NPY_FLOAT32:
    data_type = C_SHUM_REAL;
    size_in = 32;
    break;
  case NPY_INT32:
    data_type = C_SHUM_INTEGER;
    size_in = 32;
    break;
  default:
    PyErr_SetString(PyExc_ValueError, "Unsupported dtype for array");
    return NULL;
  }

  // Size out is 32-bit
  int64_t size_out = 32;

  // Also need the length of the array
  int64_t data_length = (int64_t) PyArray_SIZE(datain_obj);

  // And a reference to the data
  void *datain = PyArray_DATA(datain_obj);

  // The output array is 32-bit, but since the byte-swapping is going to be
  // (incorrectly, following the original utility) to be applied as 64-bit 
  // words we have to keep enough space in the array through this routine
  int64_t pad = data_length % 2;

  // Array to store the output
  void *dataout = calloc((size_t)(data_length + pad), sizeof(int32_t));
  if (dataout == NULL) {
    PyErr_SetString(PyExc_ValueError, "Unable to allocate memory");
    return NULL;
  }

  // Error message string
  int64_t msg_len = 512;
  char err_msg[msg_len];
  int64_t status;

  // Now construct the call
  status = c_shum_ieee2ibm(&data_type,
                           &data_length,
                           dataout,
                           &offset,
                           datain,
                           &stride,
                           &size_in,
                           &size_out,
                           &err_msg[0],
                           msg_len
                           );

  if (status != 0) {
    PyErr_SetString(PyExc_ValueError, &err_msg[0]);
    return NULL;
  }  

  // Create a byte array to store the output
  char *ptr_char = (char *)dataout;
  Py_ssize_t out_len = (Py_ssize_t) (data_length * sizeof(int32_t));

  // Byteswap on the way out, if needed
  if (c_shum_get_machine_endianism() == littleEndian) {
    status = c_shum_byteswap(ptr_char, 
                             (data_length + pad)/2,
                             sizeof(int64_t),
                             &err_msg[0],
                             msg_len
                             );
    if (status != 0) {
      PyErr_SetString(PyExc_ValueError, &err_msg[0]);
      return NULL;
    }
  }

  // Now create the output object
  PyObject *bytes_out = NULL;
  #if PY_MAJOR_VERSION >= 3
    bytes_out = PyBytes_FromStringAndSize(ptr_char, out_len);
  #else
    bytes_out = PyString_FromStringAndSize(ptr_char, out_len);
  #endif

  // Free the memory used by the original array
  free(dataout);
                  
  return bytes_out;

}

////////////////////////////////////////////////////////////////////////////////

static PyObject *get_shumlib_version_py(PyObject *self, PyObject *args)
{
  (void) self;
  (void) args;
  long version;
  version = (long) get_shum_data_conv_version();

  PyObject *version_out = NULL;
  version_out = PyInt_FromLong(version);
  return version_out;
}

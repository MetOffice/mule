/******************************COPYRIGHT*******************************/
/* (C) Crown copyright Met Office. All rights reserved.               */
/* For further details please refer to the file LICENCE.txt           */
/* which you should have received as part of this distribution.       */
/* *****************************COPYRIGHT******************************/
#ifndef NPY_1_7_API_VERSION
#define NPY_1_7_API_VERSION 0x00000007
#endif

#ifndef NPY_NO_DEPRECATED_API
#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION
#endif

#include <Python.h>
#include <numpy/arrayobject.h>
#include "read_wgdos_header.h"
#include "packing_wrappers.h"
#include "pio_byteswap.h"

PyMODINIT_FUNC initum_packing(void);

static PyObject *wgdos_unpack_py(PyObject *self, PyObject *args);
static PyObject *wgdos_pack_py(PyObject *self, PyObject *args);
static PyObject *get_um_version_py(PyObject *self, PyObject *args);

PyMODINIT_FUNC initum_packing(void)
{
  PyDoc_STRVAR(um_packing__doc__,
  "This extension module provides access to the UM unpacking library.\n"
  );

  PyDoc_STRVAR(wgdos_unpack__doc__,
  "Unpack UM field data which has been packed using WGDOS packing.\n\n"
  "Usage:\n"
  "   um_packing.wgdos_unpack(bytes_in, mdi)\n\n"
  "Args:\n"
  "* bytes_in - Packed field byte-array.\n"
  "* mdi      - Missing data indicator.\n\n"
  "Returns:\n"
  "  2 Dimensional numpy.ndarray containing the unpacked field.\n" 
  );

  PyDoc_STRVAR(wgdos_pack__doc__,
  "Pack a UM field using WGDOS packing.\n\n"
  "Usage:\n"
  "  um_packing.wgdos_pack(field_in, mdi, accuracy)\n\n"
  "Args:\n"
  "* field_in - 2 Dimensional numpy.ndarray containing the field.\n"
  "* mdi      - Missing data indicator.\n"
  "* accuracy - Packing accuracy (power of 2).\n\n"
  "Returns:\n"
  "  Byte-array/stream (suitable to write straight to file).\n"
  );

  PyDoc_STRVAR(get_um_version__doc__,
  "Return the UM version number used to compile the library.\n\n"
  "Returns:\n"
  "  String containing the UM version number.\n"
  );

  static PyMethodDef um_packingMethods[] = {
    {"wgdos_unpack", wgdos_unpack_py, METH_VARARGS, wgdos_unpack__doc__},
    {"wgdos_pack", wgdos_pack_py, METH_VARARGS, wgdos_pack__doc__},
    {"get_um_version", get_um_version_py, METH_VARARGS, get_um_version__doc__},
    {NULL, NULL, 0, NULL}
  };

  Py_InitModule3("um_packing", um_packingMethods, um_packing__doc__);
  import_array();
}

static PyObject *wgdos_unpack_py(PyObject *self, PyObject *args)
{
  // Setup and obtain inputs passed from python
  char *bytes_in = NULL;
  int64_t n_bytes = 0;
  double mdi = 0.0;
  // Note the argument descriptors "s#d":
  //   - s#  a string followed by its size
  //   - d   an integer
  if (!PyArg_ParseTuple(args, "s#d", &bytes_in, &n_bytes, &mdi)) return NULL;

  // Cast self to void to avoid unused paramter errors
  (void) self;

  // Status variable to store various error codes
  int64_t status = 1;

  // Setup output array object and dimensions
  PyArrayObject *npy_array_out = NULL;
  npy_intp dims[2];

  // Perform a byte swap on the byte-array, if it looks like it is needed
  if (get_machine_endianism() == littleEndian) {
    status = pio_byteswap(bytes_in, 
                          n_bytes/(int64_t)sizeof(int64_t), 
                          sizeof(int64_t));
    if (status != 0) {
      PyErr_SetString(PyExc_ValueError, "Problem in byte-swapping");
      return NULL;
    }
  }

  // Now extract the accuracy, number of rows and number of columns
  int64_t accuracy;
  int64_t cols;
  int64_t rows;
  status = read_wgdos_header(bytes_in, 
                             &accuracy,
                             &cols,
                             &rows);

  if (status != 0) {
    PyErr_SetString(PyExc_ValueError, "Problem reading WGDOS header");
    return NULL;
  }

  // Allocate space to hold the unpacked field
  double *dataout = (double*)calloc((size_t)(rows*cols), sizeof(double));
  if (dataout == NULL) {
    PyErr_SetString(PyExc_ValueError, "Unable to allocate memory for unpacking");
    return NULL;
  } 

  // Call the WGDOS unpacking code
  int64_t *ptr_64 = (int64_t *)bytes_in;
  int64_t len_comp = n_bytes/(int64_t)sizeof(double);

  char err_msg[512];

  xpnd_all_wrapper(dataout,
                   ptr_64,
                   &len_comp,
                   &cols,
                   &rows,
                   &accuracy,
                   &mdi,
                   &status,
                   &err_msg[0]);                           

  if (status != 0) {
    free(dataout);
    PyErr_SetString(PyExc_ValueError, &err_msg[0]);
    return NULL;
  }

  // Now form a numpy array object to return to python
  dims[0] = rows;
  dims[1] = cols;
  npy_array_out=(PyArrayObject *) PyArray_SimpleNewFromData(2, dims,
                                                            NPY_DOUBLE,
                                                            dataout);
  if (npy_array_out == NULL) {
    free(dataout);
    PyErr_SetString(PyExc_ValueError, "Failed to make numpy array");
    return NULL;
  }

  // Give python/numpy ownership of the memory storing the return array
  #if NPY_API_VERSION >= NPY_1_7_API_VERSION
  PyArray_ENABLEFLAGS(npy_array_out, NPY_ARRAY_OWNDATA);
  #else
  npy_array_out->flags = npy_array_out->flags | NPY_OWNDATA;
  #endif

  return (PyObject *)npy_array_out;
}

static PyObject *wgdos_pack_py(PyObject *self, PyObject *args)
{
  // Setup and obtain inputs passed from python
  PyArrayObject *datain;
  double mdi = 0.0;  
  int64_t accuracy = 0;
  // Note the argument descriptors "Odl":
  //   - O  a python object (here a numpy.ndarray)
  //   - d  an integer
  //   - l  a long integer
  if (!PyArg_ParseTuple(args, "Odl", 
                        &datain, 
                        &mdi, 
                        &accuracy)) return NULL;

  // Cast self to void to avoid unused paramter errors
  (void) self;

  npy_intp *dims = PyArray_DIMS(datain);
  int64_t rows = (int64_t) dims[0];
  int64_t cols = (int64_t) dims[1];
  double *field_ptr = (double *) PyArray_DATA(datain);

  // Allocate space for return value
  int64_t len_comp = rows*cols;
  int64_t *comp_field_ptr = 
    (int64_t*)calloc((size_t)(len_comp), sizeof(int64_t));

  int64_t status = 1;
  int64_t num_words;
  char err_msg[512];

  cmps_all_wrapper(field_ptr, 
                   comp_field_ptr, 
                   &len_comp, 
                   &cols, 
                   &rows, 
                   &accuracy, 
                   &mdi, 
                   &num_words, 
                   &status,
                   &err_msg[0]);

  if (status != 0) {
    free(comp_field_ptr);
    PyErr_SetString(PyExc_ValueError, &err_msg[0]);
    return NULL;
  }

  // Round number of words to sector size
  num_words = (num_words + 1)/2;
  
  // Construct a char pointer array
  char *ptr_char = (char *)comp_field_ptr;
  Py_ssize_t out_len = (Py_ssize_t) (num_words * (int64_t)sizeof(double));

  // Byteswap on the way out, if needed
  if (get_machine_endianism() == littleEndian) {
    status = pio_byteswap(ptr_char, 
                          num_words,
                          sizeof(int64_t));
    if (status != 0) {
      PyErr_SetString(PyExc_ValueError, "Problem in byte-swapping");
      return NULL;
    }
  }

  // Form a python string object to return to python
  PyObject *bytes_out = NULL;
  bytes_out = PyString_FromStringAndSize(ptr_char, out_len);

  // Free the memory used by the integer array
  free(comp_field_ptr);

  return bytes_out;
}


static PyObject *get_um_version_py(PyObject *self, PyObject *args)
{
  (void) self;
  (void) args;

  char version[8];
  get_um_version(&version[0]);
  PyObject *version_out = NULL;
  version_out = PyString_FromStringAndSize(version, strlen(version));
  return version_out;
}
